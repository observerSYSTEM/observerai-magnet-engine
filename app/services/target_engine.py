from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

from app.core.symbols import normalize_symbol
from app.schemas.v2 import V2IntelligenceResponse

TPMode = Literal["ATR", "RR", "MAGNET"]

MIN_EA_TARGET_DISTANCE = {
    "XAUUSD": 1.5,
    "GBPJPY": 0.12,
    "BTCUSD": 80.0,
}


class CandleLike(Protocol):
    high: float
    low: float


class MagnetLike(Protocol):
    price: float


@dataclass(frozen=True)
class TargetPlan:
    liquidity_target: float | None
    dashboard_target: float | None
    telegram_target: float | None
    ea_tp: float | None
    ea_sl: float | None
    target_type: str


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 5)


def minimum_ea_target_distance(symbol: str, current_price: float) -> float:
    normalized = normalize_symbol(symbol)
    return MIN_EA_TARGET_DISTANCE.get(normalized, max(0.05, abs(current_price) * 0.00025))


def is_meaningful_ea_target(symbol: str, current_price: float, target: float | None) -> bool:
    if target is None:
        return False
    return abs(float(target) - float(current_price)) >= minimum_ea_target_distance(symbol, current_price)


def _resolve_rr_multiple(rr_multiple: float) -> float:
    return 2.0 if rr_multiple >= 1.75 else 1.5


def _price_on_side(action: str, current_price: float, price: float | None) -> float | None:
    if price is None:
        return None
    if action == "BUY" and price > current_price:
        return price
    if action == "SELL" and price < current_price:
        return price
    if action not in {"BUY", "SELL"}:
        return price
    return None


def _magnet_price(magnet: MagnetLike | None) -> float | None:
    if magnet is None:
        return None
    return float(magnet.price)


def _first_valid(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _recent_extremes(m15_candles: Sequence[CandleLike]) -> tuple[float | None, float | None]:
    if not m15_candles:
        return None, None

    recent = list(m15_candles[-4:])
    recent_low = min(candle.low for candle in recent)
    recent_high = max(candle.high for candle in recent)
    return _round_price(recent_low), _round_price(recent_high)


def resolve_stop_price(
    *,
    action: str,
    stop_hint: str | None,
    anchor_value_low: float,
    anchor_value_high: float,
    m15_candles: Sequence[CandleLike],
) -> float | None:
    if action not in {"BUY", "SELL"} or stop_hint is None:
        return None

    recent_low, recent_high = _recent_extremes(m15_candles)
    if action == "BUY" and stop_hint == "below_value_low":
        return _round_price(anchor_value_low)
    if action == "SELL" and stop_hint == "above_value_high":
        return _round_price(anchor_value_high)
    if action == "BUY" and stop_hint == "below_recent_low":
        return recent_low
    if action == "SELL" and stop_hint == "above_recent_high":
        return recent_high
    return None


def select_liquidity_targets(
    *,
    action: str,
    current_price: float,
    nearest_magnet: MagnetLike | None,
    major_magnet: MagnetLike | None,
    v2_snapshot: V2IntelligenceResponse | None,
) -> tuple[float | None, float | None, float | None]:
    strongest_price = None
    zone_next = None
    zone_major = None

    if v2_snapshot is not None:
        strongest = v2_snapshot.liquidity_magnets.strongest_magnet
        strongest_price = _price_on_side(action, current_price, strongest.price if strongest else None)

        zone = v2_snapshot.zone_to_zone
        zone_next = _price_on_side(action, current_price, zone.next_zone)
        zone_major = _price_on_side(action, current_price, zone.major_zone)

    major_price = _price_on_side(action, current_price, _magnet_price(major_magnet))
    nearest_price = _price_on_side(action, current_price, _magnet_price(nearest_magnet))

    liquidity_target = _first_valid(strongest_price, major_price, nearest_price)
    dashboard_target = _first_valid(zone_next, zone_major, liquidity_target)
    telegram_target = dashboard_target

    return (
        _round_price(liquidity_target),
        _round_price(dashboard_target),
        _round_price(telegram_target),
    )


def compute_ea_execution(
    *,
    symbol: str,
    action: str,
    current_price: float,
    atr_m1: float | None,
    ea_sl: float | None,
    magnet_target: float | None,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
    fallback_tp: float | None = None,
) -> tuple[float | None, str]:
    if action not in {"BUY", "SELL"}:
        return None, "none"

    minimum_distance = minimum_ea_target_distance(symbol, current_price)
    def atr_target() -> float | None:
        if atr_m1 is None or atr_m1 <= 0:
            return _round_price(fallback_tp)
        atr_distance = max(atr_m1 * 1.2, minimum_distance)
        if action == "BUY":
            return _round_price(current_price + atr_distance)
        return _round_price(current_price - atr_distance)

    if tp_mode == "MAGNET":
        if is_meaningful_ea_target(symbol, current_price, magnet_target):
            return _round_price(magnet_target), "magnet"
        return atr_target(), "magnet_fallback_atr"

    if tp_mode == "RR":
        if ea_sl is not None:
            stop_distance = abs(current_price - ea_sl)
            if stop_distance > 0:
                rr_value = _resolve_rr_multiple(rr_multiple)
                target_distance = max(stop_distance * rr_value, minimum_distance)
                if action == "BUY":
                    return _round_price(current_price + target_distance), f"rr_{rr_value:.1f}"
                return _round_price(current_price - target_distance), f"rr_{rr_value:.1f}"
        return atr_target(), "rr_fallback_atr"

    return atr_target(), "atr"


def build_target_plan(
    *,
    symbol: str,
    action: str,
    current_price: float,
    atr_m1: float,
    stop_hint: str | None,
    nearest_magnet: MagnetLike | None,
    major_magnet: MagnetLike | None,
    v2_snapshot: V2IntelligenceResponse | None,
    anchor_value_low: float,
    anchor_value_high: float,
    m15_candles: Sequence[CandleLike],
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> TargetPlan:
    liquidity_target, dashboard_target, telegram_target = select_liquidity_targets(
        action=action,
        current_price=current_price,
        nearest_magnet=nearest_magnet,
        major_magnet=major_magnet,
        v2_snapshot=v2_snapshot,
    )
    ea_sl = resolve_stop_price(
        action=action,
        stop_hint=stop_hint,
        anchor_value_low=anchor_value_low,
        anchor_value_high=anchor_value_high,
        m15_candles=m15_candles,
    )
    ea_tp, target_type = compute_ea_execution(
        symbol=symbol,
        action=action,
        current_price=current_price,
        atr_m1=atr_m1,
        ea_sl=ea_sl,
        magnet_target=dashboard_target or liquidity_target,
        tp_mode=tp_mode,
        rr_multiple=rr_multiple,
    )

    return TargetPlan(
        liquidity_target=liquidity_target,
        dashboard_target=dashboard_target,
        telegram_target=telegram_target,
        ea_tp=ea_tp,
        ea_sl=ea_sl,
        target_type=target_type,
    )


def recompute_signal_ea_plan(
    *,
    symbol: str,
    action: str,
    current_price: float,
    atr_m1: float | None,
    ea_sl: float | None,
    dashboard_target: float | None,
    liquidity_target: float | None,
    nearest_target: float | None,
    major_target: float | None,
    fallback_tp: float | None,
    tp_mode: TPMode = "ATR",
    rr_multiple: float = 1.5,
) -> tuple[float | None, str]:
    magnet_target = _first_valid(dashboard_target, liquidity_target, major_target, nearest_target, fallback_tp)
    return compute_ea_execution(
        symbol=symbol,
        action=action,
        current_price=current_price,
        atr_m1=atr_m1,
        ea_sl=ea_sl,
        magnet_target=magnet_target,
        tp_mode=tp_mode,
        rr_multiple=rr_multiple,
        fallback_tp=fallback_tp,
    )
