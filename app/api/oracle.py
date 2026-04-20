from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.schemas.oracle import (
    IntentOut,
    MagnetInfo,
    MidPointOut,
    MidTargetsOut,
    MomentumOut,
    OracleEvaluateRequest,
    OracleEvaluateResponse,
    StructureOut,
    SweepOut,
)
from app.db.session import get_db
from app.services.adr_engine import DailyCandle as AdrDailyCandle, compute_adr_state
from app.services.anchor_engine import (
    Candle as AnchorCandle,
    compute_anchor_state,
    get_london_0801_candle,
    infer_anchor_bias,
)
from app.services.confidence_engine import score_signal
from app.services.event_engine import detect_m15_event
from app.services.intent_engine import build_trade_intent, resolve_bias
from app.services.level_engine import Candle as DailyLevelCandle, compute_daily_levels
from app.services.magnet_engine import Candle as M15Candle, Magnet, compute_xauusd_magnet_map
from app.services.market_context_engine import (
    classify_candle_momentum,
    detect_liquidity_sweep,
    detect_structure,
)
from app.services.midlevel_engine import MidPoint, compute_mid_targets
from app.services.performance_service import (
    build_signal_outcome_seed,
    create_signal_outcome,
    evaluate_open_signal_outcomes,
)
from app.services.signal_service import save_evaluated_signal
from app.services.telegram_service import deliver_signal_alert

router = APIRouter()


@dataclass(frozen=True)
class OracleEvaluationArtifacts:
    """Internal evaluation bundle used for response and outcome persistence."""

    response: OracleEvaluateResponse
    anchor_value_low: float
    anchor_value_high: float
    m15_candles: list[M15Candle]


def _event_direction(event_type: str) -> str | None:
    if "above" in event_type:
        return "bullish"
    if "below" in event_type:
        return "bearish"
    return None


def _infer_trading_day_utc(payload: OracleEvaluateRequest) -> datetime:
    """Infer the trading day from the latest provided M1 candle."""

    latest_utc = max(candle.time.astimezone(timezone.utc) for candle in payload.m1_candles)
    return datetime(latest_utc.year, latest_utc.month, latest_utc.day, tzinfo=timezone.utc)


def _to_magnet_info(magnet: Magnet | None) -> MagnetInfo | None:
    if magnet is None:
        return None

    return MagnetInfo(
        name=magnet.name,
        price=magnet.price,
        direction=magnet.direction,
        strength=magnet.strength,
        source=magnet.source,
        rank_score=magnet.rank_score,
        distance=magnet.distance,
    )


def _to_mid_point(midpoint: MidPoint | None) -> MidPointOut | None:
    if midpoint is None:
        return None

    return MidPointOut(name=midpoint.name, price=midpoint.price)


def _build_demo_request() -> OracleEvaluateRequest:
    """Build the demo payload used by the temporary GET endpoint."""

    return OracleEvaluateRequest(
        symbol="XAUUSD",
        current_price=3358.40,
        prev_m15_close=3350.10,
        m1_candles=[
            {
                "time": "2026-04-19T06:59:00Z",
                "open": 3347.20,
                "high": 3348.00,
                "low": 3346.90,
                "close": 3347.80,
            },
            {
                "time": "2026-04-19T07:00:00Z",
                "open": 3347.80,
                "high": 3348.10,
                "low": 3347.40,
                "close": 3347.95,
            },
            {
                "time": "2026-04-19T07:01:00Z",
                "open": 3348.20,
                "high": 3351.10,
                "low": 3346.80,
                "close": 3350.40,
            },
            {
                "time": "2026-04-19T07:02:00Z",
                "open": 3350.40,
                "high": 3350.70,
                "low": 3349.90,
                "close": 3350.10,
            },
        ],
        m15_candles=[
            {"time": "2026-04-19T10:00:00", "open": 3346.0, "high": 3349.0, "low": 3344.8, "close": 3348.5},
            {"time": "2026-04-19T10:15:00", "open": 3348.5, "high": 3350.5, "low": 3347.9, "close": 3350.1},
            {"time": "2026-04-19T10:30:00", "open": 3350.1, "high": 3352.4, "low": 3349.6, "close": 3351.8},
            {"time": "2026-04-19T10:45:00", "open": 3351.8, "high": 3354.0, "low": 3351.2, "close": 3353.2},
            {"time": "2026-04-19T11:00:00", "open": 3353.2, "high": 3355.8, "low": 3352.8, "close": 3354.9},
            {"time": "2026-04-19T11:15:00", "open": 3354.9, "high": 3357.2, "low": 3354.4, "close": 3356.3},
            {"time": "2026-04-19T11:30:00", "open": 3356.3, "high": 3359.1, "low": 3355.8, "close": 3358.4},
        ],
        daily_candles_for_levels=[
            {"time": "2026-04-19", "open": 3348.20, "high": 3360.00, "low": 3344.00, "close": 3358.40},
            {"time": "2026-04-18", "open": 3331.00, "high": 3361.40, "low": 3329.80, "close": 3348.00},
        ],
        daily_candles_for_adr=[
            {"time": "2026-04-18", "open": 3331.00, "high": 3361.40, "low": 3329.80, "close": 3348.00},
            {"time": "2026-04-17", "open": 3318.00, "high": 3348.20, "low": 3310.00, "close": 3330.00},
            {"time": "2026-04-16", "open": 3348.00, "high": 3368.00, "low": 3335.00, "close": 3320.00},
            {"time": "2026-04-15", "open": 3302.00, "high": 3334.00, "low": 3296.00, "close": 3318.00},
            {"time": "2026-04-14", "open": 3280.00, "high": 3315.00, "low": 3279.00, "close": 3301.00},
        ],
        atr_m1=1.10,
    )


def _evaluate_oracle_payload_artifacts(payload: OracleEvaluateRequest) -> OracleEvaluationArtifacts:
    """Run the full oracle evaluation and return persistence-friendly artifacts."""

    daily_for_levels = [
        DailyLevelCandle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.daily_candles_for_levels
    ]
    daily_for_adr = [
        AdrDailyCandle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.daily_candles_for_adr
    ]
    m1_candles = [
        AnchorCandle(
            time=candle.time.astimezone(timezone.utc),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.m1_candles
    ]
    m15_candles = [
        M15Candle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.m15_candles
    ]

    levels = compute_daily_levels(payload.symbol, daily_for_levels)
    adr_state = compute_adr_state(
        symbol=payload.symbol,
        completed_daily_candles=daily_for_adr,
        day_open=levels.day_open,
        current_price=payload.current_price,
        lookback_days=5,
    )

    anchor_candle = get_london_0801_candle(m1_candles, _infer_trading_day_utc(payload))
    anchor = compute_anchor_state(
        symbol=payload.symbol,
        anchor_candle=anchor_candle,
        atr_m1=payload.atr_m1,
    )
    bias = infer_anchor_bias(anchor, payload.current_price)

    magnet_map = compute_xauusd_magnet_map(
        current_price=payload.current_price,
        m15_candles=m15_candles,
        pdh=levels.pdh,
        pdl=levels.pdl,
        eq=levels.eq,
        adr_high=adr_state.adr_high,
        adr_low=adr_state.adr_low,
        tolerance=0.60,
    )
    event_type = detect_m15_event(
        prev_close=payload.prev_m15_close,
        curr_close=payload.current_price,
        eq=levels.eq,
        discount_high=anchor.discount_high,
        premium_low=anchor.premium_low,
        value_high=anchor.value_high,
        value_low=anchor.value_low,
        pdh=levels.pdh,
        pdl=levels.pdl,
    )
    sweep = detect_liquidity_sweep(m15_candles)
    structure = detect_structure(m15_candles, anchor.anchor_direction)
    momentum = classify_candle_momentum(m15_candles[-1])

    bullish_selection = magnet_map["bullish"]
    bearish_selection = magnet_map["bearish"]
    resolved_bias = resolve_bias(
        anchor_direction=anchor.anchor_direction,
        event_type=event_type,
        current_price=payload.current_price,
        value_low=anchor.value_low,
        value_high=anchor.value_high,
        bullish_nearest_magnet=bullish_selection.nearest,
        bullish_major_magnet=bullish_selection.major,
        bearish_nearest_magnet=bearish_selection.nearest,
        bearish_major_magnet=bearish_selection.major,
        structure=structure,
        sweep=sweep,
        momentum=momentum,
    )

    if resolved_bias.startswith("bullish"):
        selection = bullish_selection
    elif resolved_bias.startswith("bearish"):
        selection = bearish_selection
    else:
        event_direction = _event_direction(event_type)
        if event_direction == "bullish":
            selection = bullish_selection
        elif event_direction == "bearish":
            selection = bearish_selection
        elif "bullish" in bias:
            selection = bullish_selection
        elif "bearish" in bias:
            selection = bearish_selection
        else:
            selection = bullish_selection if payload.current_price > levels.eq else bearish_selection

    nearest = selection.nearest
    major = selection.major
    magnet_path = selection.candidates
    mid_targets = compute_mid_targets(
        current_price=payload.current_price,
        bias=resolved_bias,
        anchor_high=anchor.anchor_high,
        anchor_low=anchor.anchor_low,
        daily_eq=levels.eq,
        m15_candles=m15_candles,
    )
    intent = build_trade_intent(
        resolved_bias=resolved_bias,
        event_type=event_type,
        nearest_magnet=nearest,
        major_magnet=major,
        structure=structure,
        sweep=sweep,
        momentum=momentum,
        mid_targets=mid_targets,
    )
    confidence = score_signal(
        event_type=event_type,
        bias=resolved_bias,
        anchor_direction=anchor.anchor_direction,
        anchor_type=anchor.anchor_type,
        adr_used_pct=adr_state.adr_used_pct,
        has_nearest_magnet=nearest is not None,
        has_major_magnet=major is not None,
        magnet_path_depth=len(magnet_path),
        sweep_type=sweep.type,
        sweep_strength=sweep.strength,
        structure_type=structure.type,
        structure_direction=structure.direction,
        momentum_classification=momentum.classification,
        momentum_direction=momentum.direction,
        mid_flow=mid_targets.flow,
    )

    target_label = f"{intent.target:.5f}" if intent.target is not None else "none"
    message = (
        f"{payload.symbol} action={intent.action} target={target_label} | "
        f"resolved_bias={resolved_bias} | event={event_type} | "
        f"structure={structure.type}:{structure.direction} | "
        f"sweep={sweep.type}:{sweep.strength:.2f} | "
        f"momentum={momentum.classification}:{momentum.direction} | "
        f"mid_flow={mid_targets.flow} | "
        f"nearest={nearest.name if nearest else 'none'} | "
        f"major={major.name if major else 'none'} | "
        f"ADR={adr_state.adr_used_pct}%"
    )

    response = OracleEvaluateResponse(
        symbol=payload.symbol,
        current_price=payload.current_price,
        bias=bias,
        resolved_bias=resolved_bias,
        event_type=event_type,
        anchor_direction=anchor.anchor_direction,
        anchor_type=anchor.anchor_type,
        anchor_note=anchor.note,
        adr=adr_state.adr,
        adr_used_pct=adr_state.adr_used_pct,
        adr_state=adr_state.adr_state,
        nearest_magnet=_to_magnet_info(nearest),
        major_magnet=_to_magnet_info(major),
        magnet_path=[info for info in (_to_magnet_info(magnet) for magnet in magnet_path) if info is not None],
        sweep=SweepOut(type=sweep.type, strength=sweep.strength),
        structure=StructureOut(type=structure.type, direction=structure.direction),
        momentum=MomentumOut(
            direction=momentum.direction,
            body_ratio=momentum.body_ratio,
            wick_ratio=momentum.wick_ratio,
            classification=momentum.classification,
        ),
        mid_targets=MidTargetsOut(
            current_mid=_to_mid_point(mid_targets.current_mid),
            next_mid=_to_mid_point(mid_targets.next_mid),
            flow=mid_targets.flow,
        ),
        intent=IntentOut(
            action=intent.action,
            entry_type=intent.entry_type,
            reason=intent.reason,
            target=intent.target,
            stop_hint=intent.stop_hint,
        ),
        confidence=confidence,
        message=message,
    )
    return OracleEvaluationArtifacts(
        response=response,
        anchor_value_low=anchor.value_low,
        anchor_value_high=anchor.value_high,
        m15_candles=m15_candles,
    )


def _evaluate_oracle_payload(payload: OracleEvaluateRequest) -> OracleEvaluateResponse:
    """Run the full oracle evaluation using caller-supplied market data."""

    return _evaluate_oracle_payload_artifacts(payload).response


@router.get("/oracle/evaluate", response_model=OracleEvaluateResponse)
def evaluate_oracle() -> OracleEvaluateResponse:
    """Run the temporary demo evaluation using baked-in sample data."""

    return _evaluate_oracle_payload(_build_demo_request())


@router.post("/oracle/evaluate", response_model=OracleEvaluateResponse)
def evaluate_oracle_post(
    payload: OracleEvaluateRequest,
    _: None = Depends(rate_limit("oracle_evaluate", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> OracleEvaluateResponse:
    """Evaluate live oracle input supplied by the caller."""

    artifacts = _evaluate_oracle_payload_artifacts(payload)
    evaluate_open_signal_outcomes(
        db,
        symbol=payload.symbol,
        current_price=payload.current_price,
    )
    saved_signal = save_evaluated_signal(db, artifacts.response)
    outcome_seed = build_signal_outcome_seed(
        response=artifacts.response,
        anchor_value_low=artifacts.anchor_value_low,
        anchor_value_high=artifacts.anchor_value_high,
        m15_candles=artifacts.m15_candles,
    )
    create_signal_outcome(db, saved_signal, outcome_seed)
    deliver_signal_alert(db, saved_signal)
    return artifacts.response
