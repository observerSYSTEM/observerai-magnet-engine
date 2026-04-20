from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class DailyCandle:
    time: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class AdrState:
    symbol: str
    adr: float
    day_open: float
    current_price: float
    adr_high: float
    adr_low: float
    adr_used_pct: float
    adr_remaining_pct: float
    adr_state: str


def compute_adr(daily_candles: Sequence[DailyCandle], lookback_days: int = 5) -> float:
    """
    Computes Average Daily Range using the previous N completed daily candles.
    Expects completed candles only, not the current live day.
    """
    if len(daily_candles) < lookback_days:
        raise ValueError(f"At least {lookback_days} completed daily candles are required.")

    ranges = []
    for candle in daily_candles[:lookback_days]:
        rng = candle.high - candle.low
        if rng <= 0:
            raise ValueError("Invalid daily candle range encountered.")
        ranges.append(rng)

    adr = sum(ranges) / len(ranges)
    return round(adr, 5)


def project_adr_levels(day_open: float, adr: float) -> tuple[float, float]:
    if adr <= 0:
        raise ValueError("ADR must be greater than zero.")

    adr_high = day_open + adr
    adr_low = day_open - adr

    return round(adr_high, 5), round(adr_low, 5)


def classify_adr_usage(adr_used_pct: float) -> str:
    if adr_used_pct < 50:
        return "healthy"
    if adr_used_pct < 80:
        return "moderate"
    if adr_used_pct <= 100:
        return "caution"
    return "stretched"


def compute_adr_state(
    symbol: str,
    completed_daily_candles: Sequence[DailyCandle],
    day_open: float,
    current_price: float,
    lookback_days: int = 5,
) -> AdrState:
    adr = compute_adr(completed_daily_candles, lookback_days=lookback_days)
    adr_high, adr_low = project_adr_levels(day_open, adr)

    move_from_open = abs(current_price - day_open)
    adr_used_pct = (move_from_open / adr) * 100 if adr > 0 else 0.0
    adr_remaining_pct = max(0.0, 100.0 - adr_used_pct)
    adr_state_name = classify_adr_usage(adr_used_pct)

    return AdrState(
        symbol=symbol,
        adr=round(adr, 5),
        day_open=round(day_open, 5),
        current_price=round(current_price, 5),
        adr_high=adr_high,
        adr_low=adr_low,
        adr_used_pct=round(adr_used_pct, 2),
        adr_remaining_pct=round(adr_remaining_pct, 2),
        adr_state=adr_state_name,
    )