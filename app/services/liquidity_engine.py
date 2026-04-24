from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from typing import Literal, Sequence


Timeframe = Literal["H1", "H4"]
MagnetSide = Literal["above", "below"]


@dataclass(frozen=True)
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class LiquidityMagnet:
    type: str
    label: str
    price: float
    side: MagnetSide
    distance: float
    strength: int
    reason: str
    rank_score: float
    touches: int = 0
    recency_index: int = 0


@dataclass(frozen=True)
class LiquiditySnapshot:
    symbol: str
    timeframe: Timeframe
    current_price: float
    strong_magnets: list[LiquidityMagnet]
    htf_magnet_bias: Literal["bullish", "bearish", "neutral"]


TYPE_BONUS = {
    "equal_highs": 34.0,
    "equal_lows": 34.0,
    "previous_day_high": 26.0,
    "previous_day_low": 26.0,
    "weekly_high": 30.0,
    "weekly_low": 30.0,
    "round_number": 18.0,
    "imbalance": 22.0,
}

TIMEFRAME_BONUS = {"H1": 10.0, "H4": 20.0}
ROUND_STEPS = {"XAUUSD": 5.0, "GBPJPY": 0.5, "BTCUSD": 500.0}
EQUAL_TOLERANCE = {"XAUUSD": 0.6, "GBPJPY": 0.08, "BTCUSD": 60.0}
DISTANCE_NORM = {"XAUUSD": 5.0, "GBPJPY": 0.25, "BTCUSD": 250.0}
WEEKLY_LOOKBACK = {"H1": 120, "H4": 30}
MAX_RANKED_MAGNETS = 8


def _round_price(value: float) -> float:
    return round(value, 5)


def _label_for_type(magnet_type: str) -> str:
    label_map = {
        "equal_highs": "Equal Highs",
        "equal_lows": "Equal Lows",
        "previous_day_high": "Previous Day High",
        "previous_day_low": "Previous Day Low",
        "weekly_high": "Weekly High",
        "weekly_low": "Weekly Low",
        "round_number": "Round Number",
        "imbalance": "Unfilled Imbalance",
    }
    return label_map.get(magnet_type, magnet_type.replace("_", " ").title())


def _symbol_step(symbol: str, config: dict[str, float], default: float) -> float:
    return config.get(symbol.upper(), default)


def _magnet_side(price: float, current_price: float) -> MagnetSide:
    return "above" if price >= current_price else "below"


def _cluster_levels(
    values: list[tuple[int, float]],
    tolerance: float,
) -> list[tuple[float, int, int]]:
    if not values:
        return []

    ordered = sorted(values, key=lambda item: item[1])
    clusters: list[list[tuple[int, float]]] = [[ordered[0]]]

    for candidate in ordered[1:]:
        last_price = clusters[-1][-1][1]
        if abs(candidate[1] - last_price) <= tolerance:
            clusters[-1].append(candidate)
        else:
            clusters.append([candidate])

    grouped: list[tuple[float, int, int]] = []
    for cluster in clusters:
        average_price = sum(price for _, price in cluster) / len(cluster)
        last_touch = max(index for index, _ in cluster)
        grouped.append((_round_price(average_price), len(cluster), last_touch))
    return grouped


def _equal_level_magnets(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    candles: Sequence[Candle],
) -> list[LiquidityMagnet]:
    tolerance = _symbol_step(symbol, EQUAL_TOLERANCE, 0.5)
    highs = list(enumerate(candle.high for candle in candles))
    lows = list(enumerate(candle.low for candle in candles))
    magnets: list[LiquidityMagnet] = []

    for price, touches, last_touch in _cluster_levels(highs, tolerance):
        if touches < 2:
            continue
        magnets.append(
            _build_liquidity_magnet(
                symbol=symbol,
                timeframe=timeframe,
                magnet_type="equal_highs",
                price=price,
                current_price=current_price,
                touches=touches,
                recency_index=last_touch,
                reason=f"Repeated {timeframe} highs with unfilled upside liquidity",
            )
        )

    for price, touches, last_touch in _cluster_levels(lows, tolerance):
        if touches < 2:
            continue
        magnets.append(
            _build_liquidity_magnet(
                symbol=symbol,
                timeframe=timeframe,
                magnet_type="equal_lows",
                price=price,
                current_price=current_price,
                touches=touches,
                recency_index=last_touch,
                reason=f"Repeated {timeframe} lows with unfilled downside liquidity",
            )
        )

    return magnets


def _daily_reference_magnets(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    pdh: float,
    pdl: float,
    recency_index: int,
) -> list[LiquidityMagnet]:
    return [
        _build_liquidity_magnet(
            symbol=symbol,
            timeframe=timeframe,
            magnet_type="previous_day_high",
            price=_round_price(pdh),
            current_price=current_price,
            touches=1,
            recency_index=recency_index,
            reason=f"Previous day high remains a visible liquidity pool on {timeframe}.",
        ),
        _build_liquidity_magnet(
            symbol=symbol,
            timeframe=timeframe,
            magnet_type="previous_day_low",
            price=_round_price(pdl),
            current_price=current_price,
            touches=1,
            recency_index=recency_index,
            reason=f"Previous day low remains a visible liquidity pool on {timeframe}.",
        ),
    ]


def _weekly_reference_magnets(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    candles: Sequence[Candle],
) -> list[LiquidityMagnet]:
    lookback = WEEKLY_LOOKBACK[timeframe]
    subset = list(candles[-lookback:]) if len(candles) > lookback else list(candles)
    if not subset:
        return []

    highest_index, highest = max(enumerate(subset), key=lambda item: item[1].high)
    lowest_index, lowest = min(enumerate(subset), key=lambda item: item[1].low)
    return [
        _build_liquidity_magnet(
            symbol=symbol,
            timeframe=timeframe,
            magnet_type="weekly_high",
            price=_round_price(highest.high),
            current_price=current_price,
            touches=1,
            recency_index=highest_index,
            reason=f"Weekly high stands above price as a higher-timeframe draw on liquidity.",
        ),
        _build_liquidity_magnet(
            symbol=symbol,
            timeframe=timeframe,
            magnet_type="weekly_low",
            price=_round_price(lowest.low),
            current_price=current_price,
            touches=1,
            recency_index=lowest_index,
            reason=f"Weekly low stands below price as a higher-timeframe draw on liquidity.",
        ),
    ]


def _round_number_magnets(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    recency_index: int,
) -> list[LiquidityMagnet]:
    step = _symbol_step(symbol, ROUND_STEPS, 5.0)
    if step <= 0:
        return []

    base = floor(current_price / step) * step
    magnets: list[LiquidityMagnet] = []
    for offset in (-2, -1, 1, 2):
        price = _round_price(base + (offset * step))
        if abs(price - current_price) < 1e-9:
            continue
        magnets.append(
            _build_liquidity_magnet(
                symbol=symbol,
                timeframe=timeframe,
                magnet_type="round_number",
                price=price,
                current_price=current_price,
                touches=1,
                recency_index=recency_index,
                reason=f"Round-number liquidity often accumulates around {price:.2f} on {timeframe}.",
            )
        )
    return magnets


def _imbalance_magnets(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    candles: Sequence[Candle],
) -> list[LiquidityMagnet]:
    magnets: list[LiquidityMagnet] = []
    if len(candles) < 3:
        return magnets

    for index in range(2, len(candles)):
        left = candles[index - 2]
        right = candles[index]

        if right.low > left.high:
            gap_low = left.high
            gap_high = right.low
            midpoint = _round_price((gap_low + gap_high) / 2.0)
            unfilled = all(candle.low > gap_low for candle in candles[index + 1 :])
            if unfilled:
                magnets.append(
                    _build_liquidity_magnet(
                        symbol=symbol,
                        timeframe=timeframe,
                        magnet_type="imbalance",
                        price=midpoint,
                        current_price=current_price,
                        touches=1,
                        recency_index=index,
                        reason=f"Unfilled bullish {timeframe} imbalance leaves a magnet near {midpoint:.2f}.",
                    )
                )

        if right.high < left.low:
            gap_high = left.low
            gap_low = right.high
            midpoint = _round_price((gap_low + gap_high) / 2.0)
            unfilled = all(candle.high < gap_high for candle in candles[index + 1 :])
            if unfilled:
                magnets.append(
                    _build_liquidity_magnet(
                        symbol=symbol,
                        timeframe=timeframe,
                        magnet_type="imbalance",
                        price=midpoint,
                        current_price=current_price,
                        touches=1,
                        recency_index=index,
                        reason=f"Unfilled bearish {timeframe} imbalance leaves a magnet near {midpoint:.2f}.",
                    )
                )

    return magnets


def _build_liquidity_magnet(
    *,
    symbol: str,
    timeframe: Timeframe,
    magnet_type: str,
    price: float,
    current_price: float,
    touches: int,
    recency_index: int,
    reason: str,
) -> LiquidityMagnet:
    distance = round(abs(price - current_price), 5)
    distance_scale = _symbol_step(symbol, DISTANCE_NORM, 5.0)
    type_bonus = TYPE_BONUS.get(magnet_type, 12.0)
    recency_bonus = min(14.0, max(0.0, recency_index) * 0.35)
    touch_bonus = min(18.0, max(0, touches - 1) * 6.0)
    distance_penalty = min(32.0, (distance / max(distance_scale, 1e-9)) * 4.0)
    rank_score = TIMEFRAME_BONUS[timeframe] + type_bonus + touch_bonus + recency_bonus - distance_penalty
    strength = max(1, min(99, int(round(rank_score))))
    return LiquidityMagnet(
        type=magnet_type,
        label=_label_for_type(magnet_type),
        price=_round_price(price),
        side=_magnet_side(price, current_price),
        distance=distance,
        strength=strength,
        reason=reason,
        rank_score=round(rank_score, 2),
        touches=touches,
        recency_index=recency_index,
    )


def _dedupe_ranked_magnets(
    *,
    symbol: str,
    magnets: Sequence[LiquidityMagnet],
) -> list[LiquidityMagnet]:
    tolerance = _symbol_step(symbol, EQUAL_TOLERANCE, 0.5) * 1.2
    selected: list[LiquidityMagnet] = []
    for magnet in sorted(
        magnets,
        key=lambda item: (item.rank_score, item.strength, -item.distance, item.recency_index),
        reverse=True,
    ):
        if any(
            existing.side == magnet.side and abs(existing.price - magnet.price) <= tolerance
            for existing in selected
        ):
            continue
        selected.append(magnet)
        if len(selected) >= MAX_RANKED_MAGNETS:
            break
    return selected


def _resolve_htf_bias(magnets: Sequence[LiquidityMagnet]) -> Literal["bullish", "bearish", "neutral"]:
    strongest_above = max((magnet.rank_score for magnet in magnets if magnet.side == "above"), default=None)
    strongest_below = max((magnet.rank_score for magnet in magnets if magnet.side == "below"), default=None)

    if strongest_above is None and strongest_below is None:
        return "neutral"
    if strongest_below is None:
        return "bullish"
    if strongest_above is None:
        return "bearish"
    if strongest_above >= strongest_below + 4.0:
        return "bullish"
    if strongest_below >= strongest_above + 4.0:
        return "bearish"
    return "neutral"


def compute_liquidity_snapshot(
    *,
    symbol: str,
    timeframe: Timeframe,
    current_price: float,
    candles: Sequence[Candle],
    pdh: float,
    pdl: float,
) -> LiquiditySnapshot:
    symbol_name = symbol.upper()
    candle_list = list(candles)
    recency_index = len(candle_list)

    magnets = []
    magnets.extend(
        _equal_level_magnets(
            symbol=symbol_name,
            timeframe=timeframe,
            current_price=current_price,
            candles=candle_list,
        )
    )
    magnets.extend(
        _daily_reference_magnets(
            symbol=symbol_name,
            timeframe=timeframe,
            current_price=current_price,
            pdh=pdh,
            pdl=pdl,
            recency_index=recency_index,
        )
    )
    magnets.extend(
        _weekly_reference_magnets(
            symbol=symbol_name,
            timeframe=timeframe,
            current_price=current_price,
            candles=candle_list,
        )
    )
    magnets.extend(
        _round_number_magnets(
            symbol=symbol_name,
            timeframe=timeframe,
            current_price=current_price,
            recency_index=recency_index,
        )
    )
    magnets.extend(
        _imbalance_magnets(
            symbol=symbol_name,
            timeframe=timeframe,
            current_price=current_price,
            candles=candle_list,
        )
    )

    ranked = _dedupe_ranked_magnets(symbol=symbol_name, magnets=magnets)
    return LiquiditySnapshot(
        symbol=symbol_name,
        timeframe=timeframe,
        current_price=_round_price(current_price),
        strong_magnets=ranked,
        htf_magnet_bias=_resolve_htf_bias(ranked),
    )
