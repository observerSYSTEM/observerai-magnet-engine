from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence, Optional


@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class Magnet:
    name: str
    price: float
    direction: str  # bullish or bearish
    strength: float
    is_internal: bool
    is_external: bool
    source: str
    rank_score: float = 0.0
    distance: float = 0.0


@dataclass
class MagnetSelection:
    direction: str
    nearest: Optional[Magnet]
    major: Optional[Magnet]
    candidates: list[Magnet]


def is_swing_high(candles: Sequence[Candle], idx: int, left: int = 2, right: int = 2) -> bool:
    if idx - left < 0 or idx + right >= len(candles):
        return False

    h = candles[idx].high

    for i in range(idx - left, idx):
        if candles[i].high >= h:
            return False
    for i in range(idx + 1, idx + right + 1):
        if candles[i].high > h:
            return False

    return True


def is_swing_low(candles: Sequence[Candle], idx: int, left: int = 2, right: int = 2) -> bool:
    if idx - left < 0 or idx + right >= len(candles):
        return False

    l = candles[idx].low

    for i in range(idx - left, idx):
        if candles[i].low <= l:
            return False
    for i in range(idx + 1, idx + right + 1):
        if candles[i].low < l:
            return False

    return True


def find_internal_swing_magnets(
    candles: Sequence[Candle],
    current_price: float,
    lookback: int = 120,
) -> list[Magnet]:
    """
    Finds recent M15 swing highs/lows to act as internal liquidity magnets.
    Assumes candles are oldest -> newest.
    """
    subset = candles[-lookback:] if len(candles) > lookback else candles
    magnets: list[Magnet] = []

    for idx in range(len(subset)):
        c = subset[idx]

        if is_swing_high(subset, idx):
            direction = "bullish" if c.high > current_price else "bearish"
            strength = 4.0
            magnets.append(
                Magnet(
                    name="swing_high",
                    price=round(c.high, 5),
                    direction="bullish",
                    strength=strength,
                    is_internal=True,
                    is_external=False,
                    source="m15_swing",
                )
            )

        if is_swing_low(subset, idx):
            magnets.append(
                Magnet(
                    name="swing_low",
                    price=round(c.low, 5),
                    direction="bearish",
                    strength=4.0,
                    is_internal=True,
                    is_external=False,
                    source="m15_swing",
                )
            )

    return magnets


def cluster_equal_levels(
    levels: list[float],
    tolerance: float,
) -> list[tuple[float, int]]:
    """
    Clusters similar highs or lows.
    Returns [(cluster_price, count), ...]
    """
    if not levels:
        return []

    levels = sorted(levels)
    clusters: list[list[float]] = [[levels[0]]]

    for price in levels[1:]:
        if abs(price - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(price)
        else:
            clusters.append([price])

    output = []
    for cluster in clusters:
        avg_price = sum(cluster) / len(cluster)
        output.append((round(avg_price, 5), len(cluster)))

    return output


def find_equal_high_low_magnets(
    candles: Sequence[Candle],
    tolerance: float,
    lookback: int = 150,
) -> list[Magnet]:
    subset = candles[-lookback:] if len(candles) > lookback else candles

    highs = [c.high for c in subset]
    lows = [c.low for c in subset]

    high_clusters = cluster_equal_levels(highs, tolerance)
    low_clusters = cluster_equal_levels(lows, tolerance)

    magnets: list[Magnet] = []

    for price, count in high_clusters:
        if count >= 2:
            magnets.append(
                Magnet(
                    name="equal_highs",
                    price=price,
                    direction="bullish",
                    strength=5.0 + min(count, 5),
                    is_internal=True,
                    is_external=False,
                    source="m15_eqh",
                )
            )

    for price, count in low_clusters:
        if count >= 2:
            magnets.append(
                Magnet(
                    name="equal_lows",
                    price=price,
                    direction="bearish",
                    strength=5.0 + min(count, 5),
                    is_internal=True,
                    is_external=False,
                    source="m15_eql",
                )
            )

    return magnets


def build_external_magnets(
    pdh: float,
    pdl: float,
    eq: float,
    adr_high: float,
    adr_low: float,
) -> list[Magnet]:
    return [
        Magnet("PDH", round(pdh, 5), "bullish", 10.0, False, True, "daily"),
        Magnet("PDL", round(pdl, 5), "bearish", 10.0, False, True, "daily"),
        Magnet("EQ", round(eq, 5), "bullish", 6.0, False, True, "daily"),
        Magnet("ADR_HIGH", round(adr_high, 5), "bullish", 8.0, False, True, "adr"),
        Magnet("ADR_LOW", round(adr_low, 5), "bearish", 8.0, False, True, "adr"),
    ]


def _magnet_type_bonus(magnet: Magnet) -> float:
    if magnet.is_external and magnet.source == "daily":
        return 18.0
    if magnet.source.startswith("m15_eq"):
        return 14.0
    if magnet.source == "adr":
        return 12.0
    if magnet.is_internal:
        return 9.0
    return 6.0


def _adr_bonus(
    magnet: Magnet,
    bias_direction: str,
    adr_high: float | None,
    adr_low: float | None,
) -> float:
    if bias_direction == "bullish":
        if adr_high is None:
            return 0.0
        return 8.0 if magnet.price <= adr_high or magnet.name == "ADR_HIGH" else -18.0

    if adr_low is None:
        return 0.0
    return 8.0 if magnet.price >= adr_low or magnet.name == "ADR_LOW" else -18.0


def _score_magnet(
    current_price: float,
    magnet: Magnet,
    bias_direction: str,
    *,
    adr_high: float | None = None,
    adr_low: float | None = None,
) -> float:
    distance = abs(magnet.price - current_price)
    if distance <= 0:
        return -9999.0

    distance_score = max(0.0, 40.0 - (distance * 4.0))
    strength_score = magnet.strength * 6.0
    direction_bonus = 14.0 if magnet.direction == bias_direction else -24.0
    type_bonus = _magnet_type_bonus(magnet)
    adr_bonus = _adr_bonus(magnet, bias_direction, adr_high, adr_low)

    return round(distance_score + strength_score + direction_bonus + type_bonus + adr_bonus, 2)


def select_magnets(
    current_price: float,
    bias_direction: str,
    magnets: Sequence[Magnet],
    *,
    adr_high: float | None = None,
    adr_low: float | None = None,
) -> MagnetSelection:
    """
    bias_direction: bullish or bearish
    bullish -> only consider magnets above price
    bearish -> only consider magnets below price
    """
    if bias_direction not in {"bullish", "bearish"}:
        raise ValueError("bias_direction must be 'bullish' or 'bearish'.")

    if bias_direction == "bullish":
        candidates = [m for m in magnets if m.price > current_price]
    else:
        candidates = [m for m in magnets if m.price < current_price]

    if not candidates:
        return MagnetSelection(
            direction=bias_direction,
            nearest=None,
            major=None,
            candidates=[],
        )

    nearest = min(candidates, key=lambda m: abs(m.price - current_price))
    nearest = replace(
        nearest,
        distance=round(abs(nearest.price - current_price), 5),
        rank_score=_score_magnet(
            current_price,
            nearest,
            bias_direction,
            adr_high=adr_high,
            adr_low=adr_low,
        ),
    )

    ranked = [
        replace(
            magnet,
            distance=round(abs(magnet.price - current_price), 5),
            rank_score=_score_magnet(
                current_price,
                magnet,
                bias_direction,
                adr_high=adr_high,
                adr_low=adr_low,
            ),
        )
        for magnet in candidates
    ]
    ranked.sort(key=lambda magnet: (magnet.rank_score, -magnet.distance), reverse=True)

    major = ranked[0]

    return MagnetSelection(
        direction=bias_direction,
        nearest=nearest,
        major=major,
        candidates=ranked,
    )


def compute_xauusd_magnet_map(
    current_price: float,
    m15_candles: Sequence[Candle],
    pdh: float,
    pdl: float,
    eq: float,
    adr_high: float,
    adr_low: float,
    tolerance: float = 0.60,
) -> dict:
    """
    Main XAUUSD magnet builder.
    tolerance is the equal-high/low clustering tolerance in price units.
    """
    internal_swings = find_internal_swing_magnets(
        candles=m15_candles,
        current_price=current_price,
        lookback=120,
    )

    equal_levels = find_equal_high_low_magnets(
        candles=m15_candles,
        tolerance=tolerance,
        lookback=150,
    )

    external = build_external_magnets(
        pdh=pdh,
        pdl=pdl,
        eq=eq,
        adr_high=adr_high,
        adr_low=adr_low,
    )

    all_magnets = internal_swings + equal_levels + external

    bullish = select_magnets(
        current_price=current_price,
        bias_direction="bullish",
        magnets=all_magnets,
        adr_high=adr_high,
        adr_low=adr_low,
    )

    bearish = select_magnets(
        current_price=current_price,
        bias_direction="bearish",
        magnets=all_magnets,
        adr_high=adr_high,
        adr_low=adr_low,
    )

    return {
        "current_price": round(current_price, 5),
        "all_magnets": all_magnets,
        "bullish": bullish,
        "bearish": bearish,
    }
