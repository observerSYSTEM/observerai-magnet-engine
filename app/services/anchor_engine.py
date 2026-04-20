from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence, Optional


LONDON_WINTER_OFFSET = 0
LONDON_SUMMER_OFFSET = 1


@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class AnchorState:
    symbol: str
    anchor_time: datetime
    anchor_open: float
    anchor_high: float
    anchor_low: float
    anchor_close: float
    anchor_direction: str
    anchor_type: str
    wick_ratio: float
    body_ratio: float
    premium_low: float
    premium_high: float
    discount_low: float
    discount_high: float
    value_low: float
    value_high: float
    note: str


def _is_bst(dt_utc: datetime) -> bool:
    """
    Approximate British Summer Time.
    Last Sunday in March to last Sunday in October.
    """
    year = dt_utc.year

    def last_sunday(year_: int, month_: int) -> datetime:
        d = datetime(year_, month_ + 1, 1, tzinfo=timezone.utc) - timedelta(days=1) if month_ < 12 else datetime(year_ + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
        while d.weekday() != 6:
            d -= timedelta(days=1)
        return d

    march = last_sunday(year, 3)
    october = last_sunday(year, 10)

    start = datetime(year, 3, march.day, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, 10, october.day, 1, 0, 0, tzinfo=timezone.utc)

    return start <= dt_utc < end


def london_offset_hours(dt_utc: datetime) -> int:
    return LONDON_SUMMER_OFFSET if _is_bst(dt_utc) else LONDON_WINTER_OFFSET


def london_time_to_utc(day_utc: datetime, hour: int, minute: int) -> datetime:
    """
    Build London local time for a given UTC date and convert back to UTC.
    """
    offset = london_offset_hours(day_utc)
    london_midnight_utc = datetime(day_utc.year, day_utc.month, day_utc.day, 0, 0, tzinfo=timezone.utc) - timedelta(hours=offset)
    return london_midnight_utc + timedelta(hours=hour, minutes=minute)


def get_london_0801_candle(m1_candles: Sequence[Candle], trading_day_utc: datetime) -> Candle:
    """
    Finds the candle matching London 08:01 for the requested trading day.
    Expects candle.time in UTC.
    """
    target = london_time_to_utc(trading_day_utc, 8, 1)

    for candle in m1_candles:
        if candle.time == target:
            return candle

    raise ValueError(f"08:01 London candle not found for {trading_day_utc.date()}")


def classify_anchor(
    candle: Candle,
    wick_reject_thresh: float = 0.62,
    body_accept_thresh: float = 0.55,
) -> tuple[str, str, float, float]:
    rng = candle.high - candle.low
    if rng <= 0:
        raise ValueError("Invalid 08:01 anchor candle range.")

    body = abs(candle.close - candle.open)
    wick = rng - body

    body_ratio = body / rng
    wick_ratio = wick / rng

    direction = "bullish" if candle.close >= candle.open else "bearish"

    if wick_ratio >= wick_reject_thresh:
        anchor_type = "rejection"
    elif body_ratio >= body_accept_thresh:
        anchor_type = "acceptance"
    else:
        anchor_type = "neutral"

    return direction, anchor_type, round(wick_ratio, 4), round(body_ratio, 4)


def build_anchor_zones(
    candle: Candle,
    atr_m1: float,
    zone_atr_mult: float = 0.8,
) -> dict:
    """
    Premium around anchor high, discount around anchor low,
    value between anchor open and close.
    """
    if atr_m1 <= 0:
        raise ValueError("ATR(M1) must be greater than zero.")

    z = zone_atr_mult * atr_m1

    premium_low = candle.high - z
    premium_high = candle.high + z

    discount_low = candle.low - (1.5 * z)
    discount_high = candle.low + (0.5 * z)

    value_low = min(candle.open, candle.close)
    value_high = max(candle.open, candle.close)

    return {
        "premium_low": round(premium_low, 5),
        "premium_high": round(premium_high, 5),
        "discount_low": round(discount_low, 5),
        "discount_high": round(discount_high, 5),
        "value_low": round(value_low, 5),
        "value_high": round(value_high, 5),
    }


def compute_anchor_state(
    symbol: str,
    anchor_candle: Candle,
    atr_m1: float,
    wick_reject_thresh: float = 0.62,
    body_accept_thresh: float = 0.55,
    zone_atr_mult: float = 0.8,
) -> AnchorState:
    direction, anchor_type, wick_ratio, body_ratio = classify_anchor(
        candle=anchor_candle,
        wick_reject_thresh=wick_reject_thresh,
        body_accept_thresh=body_accept_thresh,
    )

    zones = build_anchor_zones(
        candle=anchor_candle,
        atr_m1=atr_m1,
        zone_atr_mult=zone_atr_mult,
    )

    note = f"Anchor08:01 dir={direction.upper()} type={anchor_type.upper()} wick={wick_ratio:.2f} body={body_ratio:.2f}"

    return AnchorState(
        symbol=symbol,
        anchor_time=anchor_candle.time,
        anchor_open=round(anchor_candle.open, 5),
        anchor_high=round(anchor_candle.high, 5),
        anchor_low=round(anchor_candle.low, 5),
        anchor_close=round(anchor_candle.close, 5),
        anchor_direction=direction,
        anchor_type=anchor_type,
        wick_ratio=wick_ratio,
        body_ratio=body_ratio,
        premium_low=zones["premium_low"],
        premium_high=zones["premium_high"],
        discount_low=zones["discount_low"],
        discount_high=zones["discount_high"],
        value_low=zones["value_low"],
        value_high=zones["value_high"],
        note=note,
    )


def infer_anchor_bias(anchor: AnchorState, current_price: float) -> str:
    """
    Converts anchor state into usable directional context.
    """
    in_premium = anchor.premium_low <= current_price <= anchor.premium_high
    in_discount = anchor.discount_low <= current_price <= anchor.discount_high
    in_value = anchor.value_low <= current_price <= anchor.value_high

    if anchor.anchor_type == "rejection":
        if in_discount:
            return "bullish_rejection_discount"
        if in_premium:
            return "bearish_rejection_premium"
        return f"{anchor.anchor_direction}_rejection_wait_zone"

    if anchor.anchor_type == "acceptance":
        if anchor.anchor_direction == "bullish":
            return "bullish_acceptance" if current_price >= anchor.value_low else "bullish_acceptance_wait_value"
        return "bearish_acceptance" if current_price <= anchor.value_high else "bearish_acceptance_wait_value"

    if in_value:
        return "neutral_in_value"
    return "neutral_outside_value"