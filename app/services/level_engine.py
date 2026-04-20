from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class DailyLevels:
    symbol: str
    pdh: float
    pdl: float
    eq: float
    day_open: float


def compute_daily_levels(symbol: str, daily_candles: Sequence[Candle]) -> DailyLevels:
    if len(daily_candles) < 2:
        raise ValueError("compute_daily_levels requires current-day and previous-day candles.")

    current_day = daily_candles[0]
    previous_day = daily_candles[1]
    pdh = round(previous_day.high, 5)
    pdl = round(previous_day.low, 5)

    return DailyLevels(
        symbol=symbol,
        pdh=pdh,
        pdl=pdl,
        eq=round((pdh + pdl) / 2.0, 5),
        day_open=round(current_day.open, 5),
    )


def compute_levels(pdh: float, pdl: float, day_open: float) -> dict:
    return {
        "pdh": pdh,
        "pdl": pdl,
        "eq": (pdh + pdl) / 2.0,
        "day_open": day_open,
    }
