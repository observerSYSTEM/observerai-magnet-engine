from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.signal import BestSignalResponse, EaLatestSignalResponse, LatestSignalResponse, StoredSignalOut
from app.services.market_state_service import get_htf_context
from app.services.signal_service import list_latest_signals
from app.services.target_engine import TPMode, minimum_ea_target_distance, recompute_signal_ea_plan
from app.utils.dedupe import ALERT_COOLDOWN_WINDOW, CONFIDENCE_CHANGE_THRESHOLD, signal_key, signal_target

logger = logging.getLogger(__name__)

MAX_CANDIDATES_PER_SYMBOL = 12
MAX_TRADEABLE_AGE = timedelta(hours=24)
EA_MIN_CONFIDENCE = 88
MIN_TARGET_DISTANCE = {
    "XAUUSD": 1.5,
    "GBPJPY": 0.12,
    "BTCUSD": 80.0,
}

LABEL_OVERRIDES = {
    "bullish_continuation": "Bullish Continuation",
    "bearish_continuation": "Bearish Continuation",
    "bullish_reversal": "Bullish Reversal",
    "bearish_reversal": "Bearish Reversal",
    "neutral_outside_value": "Neutral Outside Value",
    "neutral_wait": "Neutral Wait",
}


def _humanize_label(value: str | None) -> str:
    if not value:
        return "None"

    lowered = value.strip().lower()
    if lowered in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[lowered]

    return " ".join(part.capitalize() for part in lowered.split("_") if part) or "None"


def _compact_magnet(value) -> str | None:
    if value is None:
        return None
    return f"{value.name.lower()} {value.price:.2f}"


def _compact_lifecycle(state: str | None) -> str | None:
    if not state:
        return None
    return state.strip().lower().replace(" ", "_")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _execution_target(
    signal: StoredSignalOut,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> tuple[float | None, str]:
    return recompute_signal_ea_plan(
        symbol=signal.symbol,
        action=signal.intent.action,
        current_price=signal.current_price,
        atr_m1=signal.atr_m1,
        ea_sl=signal.ea_sl,
        dashboard_target=signal.dashboard_target,
        liquidity_target=signal.liquidity_target,
        nearest_target=signal.nearest_magnet.price if signal.nearest_magnet is not None else None,
        major_target=signal.major_magnet.price if signal.major_magnet is not None else None,
        fallback_tp=signal.ea_tp or signal.intent.target,
        tp_mode=tp_mode,
        rr_multiple=rr_multiple,
    )


def _target_distance(
    signal: StoredSignalOut,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> float:
    target, _ = _execution_target(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)
    if target is None:
        return 0.0
    return abs(target - signal.current_price)


def _minimum_target_distance(signal: StoredSignalOut) -> float:
    return MIN_TARGET_DISTANCE.get(signal.symbol.upper(), minimum_ea_target_distance(signal.symbol, signal.current_price))


def _is_directional_bias(signal: StoredSignalOut) -> bool:
    return signal.resolved_bias.startswith(("bullish", "bearish"))


def is_tradeable_signal(
    signal: StoredSignalOut,
    *,
    now: datetime | None = None,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> bool:
    observed_at = now or _utcnow()
    created_at = _to_utc(signal.created_at)
    target, _ = _execution_target(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)

    if signal.intent.action not in {"BUY", "SELL"}:
        return False
    if signal.confidence < EA_MIN_CONFIDENCE:
        return False
    if signal.lifecycle.state != "Setup Confirmed":
        return False
    if not _is_directional_bias(signal):
        return False
    if target is None:
        return False
    if _target_distance(signal, tp_mode=tp_mode, rr_multiple=rr_multiple) < _minimum_target_distance(signal):
        return False
    if observed_at - created_at > MAX_TRADEABLE_AGE:
        return False
    return True


def _rank_signal(
    signal: StoredSignalOut,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> tuple[int, int, int, float, float]:
    tradeable = 1 if is_tradeable_signal(signal, tp_mode=tp_mode, rr_multiple=rr_multiple) else 0
    directional = 1 if _is_directional_bias(signal) else 0
    created_at = _to_utc(signal.created_at).timestamp()
    return (
        tradeable,
        signal.confidence,
        directional,
        _target_distance(signal, tp_mode=tp_mode, rr_multiple=rr_multiple),
        created_at,
    )


def _dedupe_candidates(signals: list[StoredSignalOut]) -> list[StoredSignalOut]:
    accepted: list[StoredSignalOut] = []
    latest_by_key: dict[str, StoredSignalOut] = {}

    for signal in sorted(signals, key=lambda item: _to_utc(item.created_at), reverse=True):
        current_key = signal_key(
            signal.symbol,
            signal.resolved_bias,
            signal.event_type,
            signal_target(signal),
        )
        newer = latest_by_key.get(current_key)
        if newer is not None:
            within_cooldown = (_to_utc(newer.created_at) - _to_utc(signal.created_at)) <= ALERT_COOLDOWN_WINDOW
            confidence_close = abs(newer.confidence - signal.confidence) < CONFIDENCE_CHANGE_THRESHOLD
            if within_cooldown and confidence_close:
                continue

        latest_by_key[current_key] = signal
        accepted.append(signal)

    return accepted


def _build_candidate_response(
    signal: StoredSignalOut,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> BestSignalResponse:
    target, target_type = _execution_target(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)
    return BestSignalResponse(
        symbol=signal.symbol,
        action=signal.intent.action,
        bias=_humanize_label(signal.resolved_bias),
        confidence=signal.confidence,
        price=signal.current_price,
        target=target,
        target_type=target_type,
        tradeable=is_tradeable_signal(signal, tp_mode=tp_mode, rr_multiple=rr_multiple),
        reason="Highest confidence active directional setup",
    )


def select_best_signal(
    db: Session,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> BestSignalResponse:
    settings = get_settings()
    candidates: list[StoredSignalOut] = []

    for symbol in settings.runner_symbols:
        latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
        candidates.extend(_dedupe_candidates(latest.items))

    tradeable_candidates = [
        signal for signal in candidates if is_tradeable_signal(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)
    ]
    if not tradeable_candidates:
        logger.info(
            "No tradeable signal available | symbols=%s",
            ",".join(settings.runner_symbols),
        )
        return BestSignalResponse(
            tradeable=False,
            message="No strong signal available",
        )

    selected = max(
        tradeable_candidates,
        key=lambda item: _rank_signal(item, tp_mode=tp_mode, rr_multiple=rr_multiple),
    )
    selected_target, selected_target_type = _execution_target(
        selected,
        tp_mode=tp_mode,
        rr_multiple=rr_multiple,
    )
    logger.info(
        "Best signal selected | symbol=%s action=%s confidence=%s target=%s",
        selected.symbol,
        selected.intent.action,
        selected.confidence,
        selected_target,
    )
    response = _build_candidate_response(selected, tp_mode=tp_mode, rr_multiple=rr_multiple)
    response.target_type = selected_target_type
    return response


def get_latest_tradeable_signal(
    db: Session,
    symbol: str,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> LatestSignalResponse:
    latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
    candidates = _dedupe_candidates(latest.items)
    item = next(
        (
            signal
            for signal in candidates
            if is_tradeable_signal(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)
        ),
        None,
    )
    return LatestSignalResponse(symbol=latest.symbol, item=item)


def get_latest_ea_signal(
    db: Session,
    symbol: str,
    *,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> EaLatestSignalResponse:
    latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
    candidates = _dedupe_candidates(latest.items)
    signal = next(
        (
            item
            for item in candidates
            if is_tradeable_signal(item, tp_mode=tp_mode, rr_multiple=rr_multiple)
        ),
        None,
    )

    if signal is None:
        logger.info("No tradeable signal available for EA | symbol=%s", latest.symbol)
        return EaLatestSignalResponse(
            symbol=latest.symbol,
            tradeable=False,
            message="No strong signal available",
        )

    target, target_type = _execution_target(signal, tp_mode=tp_mode, rr_multiple=rr_multiple)
    logger.info(
        "EA latest signal selected | symbol=%s action=%s confidence=%s target=%s target_type=%s",
        signal.symbol,
        signal.intent.action,
        signal.confidence,
        target,
        target_type,
    )
    return EaLatestSignalResponse(
        symbol=signal.symbol,
        action=signal.intent.action,
        bias=signal.resolved_bias,
        confidence=signal.confidence,
        price=signal.current_price,
        target=target,
        ea_tp=target,
        ea_sl=signal.ea_sl,
        stop_hint=signal.intent.stop_hint,
        nearest_magnet=_compact_magnet(signal.nearest_magnet),
        major_magnet=_compact_magnet(signal.major_magnet),
        liquidity_target=signal.liquidity_target,
        dashboard_target=signal.dashboard_target,
        target_type=target_type,
        tradeable=True,
        lifecycle=_compact_lifecycle(signal.lifecycle.state),
        htf_context=get_htf_context(db, signal.symbol, signal.intent.action),
        created_at=signal.created_at,
    )
