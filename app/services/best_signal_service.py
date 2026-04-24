from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.signal import BestSignalResponse, EaLatestSignalResponse, LatestSignalResponse, StoredSignalOut
from app.services.signal_service import list_latest_signals
from app.utils.dedupe import ALERT_COOLDOWN_WINDOW, CONFIDENCE_CHANGE_THRESHOLD, signal_key

logger = logging.getLogger(__name__)

MAX_CANDIDATES_PER_SYMBOL = 12
MAX_TRADEABLE_AGE = timedelta(hours=24)
EA_MIN_CONFIDENCE = 88
MIN_TARGET_DISTANCE = {
    "XAUUSD": 0.6,
    "GBPJPY": 0.08,
    "BTCUSD": 40.0,
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


def _target_distance(signal: StoredSignalOut) -> float:
    if signal.intent.target is None:
        return 0.0
    return abs(signal.intent.target - signal.current_price)


def _minimum_target_distance(signal: StoredSignalOut) -> float:
    return MIN_TARGET_DISTANCE.get(signal.symbol.upper(), max(0.05, signal.current_price * 0.00015))


def _is_directional_bias(signal: StoredSignalOut) -> bool:
    return signal.resolved_bias.startswith(("bullish", "bearish"))


def is_tradeable_signal(signal: StoredSignalOut, *, now: datetime | None = None) -> bool:
    observed_at = now or _utcnow()
    created_at = _to_utc(signal.created_at)

    if signal.intent.action not in {"BUY", "SELL"}:
        return False
    if signal.confidence < EA_MIN_CONFIDENCE:
        return False
    if signal.lifecycle.state != "Setup Confirmed":
        return False
    if not _is_directional_bias(signal):
        return False
    if signal.intent.target is None:
        return False
    if _target_distance(signal) < _minimum_target_distance(signal):
        return False
    if observed_at - created_at > MAX_TRADEABLE_AGE:
        return False
    return True


def _rank_signal(signal: StoredSignalOut) -> tuple[int, int, int, float, float]:
    tradeable = 1 if is_tradeable_signal(signal) else 0
    directional = 1 if _is_directional_bias(signal) else 0
    created_at = _to_utc(signal.created_at).timestamp()
    return (
        tradeable,
        signal.confidence,
        directional,
        _target_distance(signal),
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
            signal.intent.target,
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


def _build_candidate_response(signal: StoredSignalOut) -> BestSignalResponse:
    return BestSignalResponse(
        symbol=signal.symbol,
        action=signal.intent.action,
        bias=_humanize_label(signal.resolved_bias),
        confidence=signal.confidence,
        price=signal.current_price,
        target=signal.intent.target,
        tradeable=is_tradeable_signal(signal),
        reason="Highest confidence active directional setup",
    )


def select_best_signal(db: Session) -> BestSignalResponse:
    settings = get_settings()
    candidates: list[StoredSignalOut] = []

    for symbol in settings.runner_symbols:
        latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
        candidates.extend(_dedupe_candidates(latest.items))

    tradeable_candidates = [signal for signal in candidates if is_tradeable_signal(signal)]
    if not tradeable_candidates:
        logger.info(
            "No tradeable signal available | symbols=%s",
            ",".join(settings.runner_symbols),
        )
        return BestSignalResponse(
            tradeable=False,
            message="No strong signal available",
        )

    selected = max(tradeable_candidates, key=_rank_signal)
    logger.info(
        "Best signal selected | symbol=%s action=%s confidence=%s target=%s",
        selected.symbol,
        selected.intent.action,
        selected.confidence,
        selected.intent.target,
    )
    return _build_candidate_response(selected)


def get_latest_tradeable_signal(db: Session, symbol: str) -> LatestSignalResponse:
    latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
    candidates = _dedupe_candidates(latest.items)
    item = next((signal for signal in candidates if is_tradeable_signal(signal)), None)
    return LatestSignalResponse(symbol=latest.symbol, item=item)


def get_latest_ea_signal(db: Session, symbol: str) -> EaLatestSignalResponse:
    latest = list_latest_signals(db, symbol, limit=MAX_CANDIDATES_PER_SYMBOL)
    candidates = _dedupe_candidates(latest.items)
    signal = next((item for item in candidates if is_tradeable_signal(item)), None)

    if signal is None:
        logger.info("No tradeable signal available for EA | symbol=%s", latest.symbol)
        return EaLatestSignalResponse(
            symbol=latest.symbol,
            tradeable=False,
            message="No strong signal available",
        )

    logger.info(
        "EA latest signal selected | symbol=%s action=%s confidence=%s target=%s",
        signal.symbol,
        signal.intent.action,
        signal.confidence,
        signal.intent.target,
    )
    return EaLatestSignalResponse(
        symbol=signal.symbol,
        action=signal.intent.action,
        bias=signal.resolved_bias,
        confidence=signal.confidence,
        price=signal.current_price,
        target=signal.intent.target,
        stop_hint=signal.intent.stop_hint,
        nearest_magnet=_compact_magnet(signal.nearest_magnet),
        major_magnet=_compact_magnet(signal.major_magnet),
        tradeable=True,
        lifecycle=_compact_lifecycle(signal.lifecycle.state),
        created_at=signal.created_at,
    )
