from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence


class CandleLike(Protocol):
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SweepState:
    """Simple liquidity sweep classification for the latest candle."""

    type: Literal["none", "buyside", "sellside"]
    strength: float


@dataclass(frozen=True)
class StructureState:
    """Recent market structure classification derived from the latest break."""

    type: Literal["none", "bos", "mss"]
    direction: Literal["neutral", "bullish", "bearish"]


@dataclass(frozen=True)
class MomentumState:
    """Body-versus-wick momentum view for the latest candle."""

    direction: Literal["neutral", "bullish", "bearish"]
    body_ratio: float
    wick_ratio: float
    classification: Literal["weak", "moderate", "strong"]


def _candle_range(candle: CandleLike) -> float:
    return max(candle.high - candle.low, 0.0)


def detect_liquidity_sweep(
    candles: Sequence[CandleLike],
    lookback: int = 20,
) -> SweepState:
    """
    Detect a simple one-candle liquidity sweep on the most recent M15 candle.

    A buyside sweep breaks recent highs but closes back beneath them.
    A sellside sweep breaks recent lows but closes back above them.
    """

    if len(candles) < 3:
        return SweepState(type="none", strength=0.0)

    latest = candles[-1]
    history = candles[-(lookback + 1):-1] if len(candles) > lookback else candles[:-1]
    if not history:
        return SweepState(type="none", strength=0.0)

    recent_high = max(candle.high for candle in history)
    recent_low = min(candle.low for candle in history)
    rng = _candle_range(latest)
    if rng <= 0:
        return SweepState(type="none", strength=0.0)

    buyside_strength = 0.0
    sellside_strength = 0.0

    if latest.high > recent_high and latest.close < recent_high:
        overshoot = latest.high - recent_high
        rejection = max(0.0, recent_high - latest.close)
        buyside_strength = min(10.0, round(((overshoot + rejection) / rng) * 5.0, 2))

    if latest.low < recent_low and latest.close > recent_low:
        overshoot = recent_low - latest.low
        rejection = max(0.0, latest.close - recent_low)
        sellside_strength = min(10.0, round(((overshoot + rejection) / rng) * 5.0, 2))

    if buyside_strength > sellside_strength and buyside_strength > 0:
        return SweepState(type="buyside", strength=buyside_strength)
    if sellside_strength > 0:
        return SweepState(type="sellside", strength=sellside_strength)
    return SweepState(type="none", strength=0.0)


def detect_structure(
    candles: Sequence[CandleLike],
    anchor_direction: str,
    lookback: int = 20,
) -> StructureState:
    """
    Detect a lightweight BOS/MSS state from the most recent close.

    BOS is used when the break direction agrees with the anchor direction.
    MSS is used when the break direction opposes the anchor direction.
    """

    if len(candles) < 3:
        return StructureState(type="none", direction="neutral")

    latest = candles[-1]
    history = candles[-(lookback + 1):-1] if len(candles) > lookback else candles[:-1]
    if not history:
        return StructureState(type="none", direction="neutral")

    recent_high = max(candle.high for candle in history)
    recent_low = min(candle.low for candle in history)

    if latest.close > recent_high:
        structure_type: Literal["bos", "mss"] = "bos" if anchor_direction == "bullish" else "mss"
        return StructureState(type=structure_type, direction="bullish")

    if latest.close < recent_low:
        structure_type = "bos" if anchor_direction == "bearish" else "mss"
        return StructureState(type=structure_type, direction="bearish")

    return StructureState(type="none", direction="neutral")


def classify_candle_momentum(candle: CandleLike) -> MomentumState:
    """
    Measure candle conviction using body-versus-wick composition.
    """

    rng = _candle_range(candle)
    if rng <= 0:
        return MomentumState(
            direction="neutral",
            body_ratio=0.0,
            wick_ratio=0.0,
            classification="weak",
        )

    body = abs(candle.close - candle.open)
    wick = max(0.0, rng - body)
    body_ratio = round(body / rng, 4)
    wick_ratio = round(wick / rng, 4)

    if candle.close > candle.open:
        direction: Literal["neutral", "bullish", "bearish"] = "bullish"
    elif candle.close < candle.open:
        direction = "bearish"
    else:
        direction = "neutral"

    if body_ratio >= 0.65:
        classification: Literal["weak", "moderate", "strong"] = "strong"
    elif body_ratio >= 0.35:
        classification = "moderate"
    else:
        classification = "weak"

    return MomentumState(
        direction=direction,
        body_ratio=body_ratio,
        wick_ratio=wick_ratio,
        classification=classification,
    )
