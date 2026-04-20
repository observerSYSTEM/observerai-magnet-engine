from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from app.services.magnet_engine import Candle, is_swing_high, is_swing_low


MidFlowName = Literal[
    "bullish_mid_to_mid",
    "bearish_mid_to_mid",
    "mid_compression",
    "no_mid_flow",
]


@dataclass(frozen=True)
class MidPoint:
    """Named midpoint used for mid-to-mid flow tracking."""

    name: str
    price: float


@dataclass(frozen=True)
class MidTargets:
    """Current and next midpoint targets for directional flow."""

    current_mid: MidPoint | None
    next_mid: MidPoint | None
    flow: MidFlowName


def compute_anchor_mid(anchor_high: float, anchor_low: float) -> MidPoint:
    return MidPoint(name="anchor_mid", price=round((anchor_high + anchor_low) / 2.0, 5))


def compute_daily_eq_mid(daily_eq: float) -> MidPoint:
    return MidPoint(name="daily_eq", price=round(daily_eq, 5))


def compute_intraday_mid(
    m15_candles: Sequence[Candle],
    lookback: int = 48,
) -> MidPoint | None:
    """
    Compute an intraday midpoint from the most recent meaningful swing high/low pair.

    When explicit swing points are unavailable, the recent range extremes are used as a
    lightweight fallback so the engine still produces a usable intraday midpoint.
    """

    if not m15_candles:
        return None

    subset = list(m15_candles[-lookback:] if len(m15_candles) > lookback else m15_candles)
    swing_highs = [candle.high for idx, candle in enumerate(subset) if is_swing_high(subset, idx)]
    swing_lows = [candle.low for idx, candle in enumerate(subset) if is_swing_low(subset, idx)]

    recent_high = swing_highs[-1] if swing_highs else max(candle.high for candle in subset)
    recent_low = swing_lows[-1] if swing_lows else min(candle.low for candle in subset)

    if recent_high <= recent_low:
        return None

    return MidPoint(name="intraday_mid", price=round((recent_high + recent_low) / 2.0, 5))


def _dedupe_mids(mids: Sequence[MidPoint]) -> list[MidPoint]:
    unique: dict[tuple[str, float], MidPoint] = {}
    for midpoint in mids:
        unique[(midpoint.name, midpoint.price)] = midpoint
    return sorted(unique.values(), key=lambda midpoint: midpoint.price)


def _infer_direction(bias: str) -> Literal["bullish", "bearish", "neutral"]:
    if "bullish" in bias:
        return "bullish"
    if "bearish" in bias:
        return "bearish"
    return "neutral"


def compute_mid_targets(
    *,
    current_price: float,
    bias: str,
    anchor_high: float,
    anchor_low: float,
    daily_eq: float,
    m15_candles: Sequence[Candle],
    compression_threshold: float = 0.75,
) -> MidTargets:
    """
    Select current and next midpoint targets for the active directional flow.
    """

    mids = [
        compute_anchor_mid(anchor_high, anchor_low),
        compute_daily_eq_mid(daily_eq),
    ]
    intraday_mid = compute_intraday_mid(m15_candles)
    if intraday_mid is not None:
        mids.append(intraday_mid)

    ordered_mids = _dedupe_mids(mids)
    direction = _infer_direction(bias)

    if direction == "bullish":
        current_mid = max(
            (midpoint for midpoint in ordered_mids if midpoint.price <= current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        next_mid = min(
            (midpoint for midpoint in ordered_mids if midpoint.price > current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        flow: MidFlowName = "bullish_mid_to_mid" if current_mid and next_mid else "no_mid_flow"
    elif direction == "bearish":
        current_mid = min(
            (midpoint for midpoint in ordered_mids if midpoint.price >= current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        next_mid = max(
            (midpoint for midpoint in ordered_mids if midpoint.price < current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        flow = "bearish_mid_to_mid" if current_mid and next_mid else "no_mid_flow"
    else:
        current_mid = max(
            (midpoint for midpoint in ordered_mids if midpoint.price <= current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        next_mid = min(
            (midpoint for midpoint in ordered_mids if midpoint.price > current_price),
            key=lambda midpoint: midpoint.price,
            default=None,
        )
        flow = "no_mid_flow"

    if current_mid and next_mid and abs(next_mid.price - current_mid.price) <= compression_threshold:
        flow = "mid_compression"

    return MidTargets(current_mid=current_mid, next_mid=next_mid, flow=flow)
