from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.symbols import normalize_symbol
from app.schemas.oracle import OracleEvaluateRequest
from app.schemas.v2 import (
    Anchor0801BiasOut,
    DiscountPremiumZoneOut,
    HighestProbabilityDirectionOut,
    HighestProbabilityScoreBreakdownOut,
    LiquidityMagnetsV2Out,
    M15MidlevelBreakOut,
    ManipulationZoneOut,
    NewsContextOut,
    V2IntelligenceResponse,
    V2LiquidityMagnetOut,
    VolatilityStateOut,
    ZonePathLevelOut,
    ZoneToZonePathOut,
)
from app.services.adr_engine import DailyCandle as AdrDailyCandle, compute_adr_state
from app.services.anchor_engine import (
    Candle as AnchorCandle,
    classify_anchor,
    get_london_0801_candle,
    london_offset_hours,
)
from app.services.level_engine import Candle as DailyLevelCandle, compute_daily_levels
from app.services.liquidity_engine import Candle as LiquidityCandle, compute_liquidity_snapshot


def _round_price(value: float | None) -> float:
    return round(float(value or 0.0), 5)


def _field_value(item, field: str) -> float:
    if isinstance(item, dict):
        return float(item[field])
    return float(getattr(item, field))


def _infer_trading_day_utc(payload: OracleEvaluateRequest) -> datetime:
    latest_utc = max(candle.time.astimezone(UTC) for candle in payload.m1_candles)
    return datetime(latest_utc.year, latest_utc.month, latest_utc.day, tzinfo=UTC)


def _to_anchor_candles(payload: OracleEvaluateRequest) -> list[AnchorCandle]:
    return [
        AnchorCandle(
            time=candle.time.astimezone(UTC),
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.m1_candles
    ]


def _to_daily_level_candles(payload: OracleEvaluateRequest) -> list[DailyLevelCandle]:
    return [
        DailyLevelCandle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.daily_candles_for_levels
    ]


def _to_adr_candles(payload: OracleEvaluateRequest) -> list[AdrDailyCandle]:
    return [
        AdrDailyCandle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in payload.daily_candles_for_adr
    ]


def _to_liquidity_candles(candles) -> list[LiquidityCandle]:
    return [
        LiquidityCandle(
            time=candle.time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
        )
        for candle in candles
    ]


def _compute_daily_context(payload: OracleEvaluateRequest) -> tuple[object, object]:
    symbol = normalize_symbol(payload.symbol)
    levels = compute_daily_levels(symbol, _to_daily_level_candles(payload))
    adr_state = compute_adr_state(
        symbol=symbol,
        completed_daily_candles=_to_adr_candles(payload),
        day_open=levels.day_open,
        current_price=payload.current_price,
        lookback_days=min(5, len(payload.daily_candles_for_adr)),
    )
    return levels, adr_state


def _anchor_type_label(anchor_type: str) -> str:
    if anchor_type == "rejection":
        return "wick_rejection"
    if anchor_type == "acceptance":
        return "body_acceptance"
    return "neutral"


def _liquidity_out(*, rank: int, timeframe: str, magnet) -> V2LiquidityMagnetOut:
    return V2LiquidityMagnetOut(
        rank=rank,
        timeframe=timeframe,  # type: ignore[arg-type]
        type=magnet.type,
        label=magnet.label,
        price=magnet.price,
        side=magnet.side,
        distance=magnet.distance,
        strength=magnet.strength,
        reason=magnet.reason,
    )


def _iter_ranked_magnets(magnets: list[V2LiquidityMagnetOut]) -> list[V2LiquidityMagnetOut]:
    return sorted(
        magnets,
        key=lambda item: (
            1 if item.timeframe == "H4" else 0,
            item.strength,
            -item.distance,
            -item.rank,
        ),
        reverse=True,
    )


def compute_0801_bias(payload: OracleEvaluateRequest) -> Anchor0801BiasOut:
    try:
        anchor_candle = get_london_0801_candle(
            _to_anchor_candles(payload),
            _infer_trading_day_utc(payload),
        )
    except ValueError:
        return Anchor0801BiasOut(reason="08:01 London anchor candle was not found in the supplied M1 data.")

    direction, raw_anchor_type, wick_ratio, body_ratio = classify_anchor(anchor_candle)
    anchor_type = _anchor_type_label(raw_anchor_type)
    bias = direction if anchor_type != "neutral" else "neutral"
    reason = (
        f"08:01 London candle formed {direction} {anchor_type.replace('_', ' ')} "
        f"(wick={wick_ratio:.2f}, body={body_ratio:.2f})."
    )

    return Anchor0801BiasOut(
        anchor_time="08:01",
        anchor_high=_round_price(anchor_candle.high),
        anchor_low=_round_price(anchor_candle.low),
        anchor_mid=_round_price((anchor_candle.high + anchor_candle.low) / 2.0),
        anchor_type=anchor_type,
        bias=bias,  # type: ignore[arg-type]
        reason=reason,
    )


def compute_discount_premium_zone(anchor: Anchor0801BiasOut, current_price: float) -> DiscountPremiumZoneOut:
    midlevel = anchor.anchor_mid
    anchor_range = max(0.0, anchor.anchor_high - anchor.anchor_low)
    mid_tolerance = max(anchor_range * 0.1, 1e-6)

    if abs(current_price - midlevel) <= mid_tolerance:
        price_position = "mid"
    elif current_price > midlevel:
        price_position = "premium"
    else:
        price_position = "discount"

    return DiscountPremiumZoneOut(
        premium_high=anchor.anchor_high,
        discount_low=anchor.anchor_low,
        midlevel=midlevel,
        price_position=price_position,  # type: ignore[arg-type]
    )


def compute_h1_h4_liquidity_magnets(payload: OracleEvaluateRequest) -> LiquidityMagnetsV2Out:
    symbol = normalize_symbol(payload.symbol)
    levels, _ = _compute_daily_context(payload)
    h1_candles = _to_liquidity_candles(payload.h1_candles or [])
    h4_candles = _to_liquidity_candles(payload.h4_candles or [])

    if not h1_candles and not h4_candles:
        return LiquidityMagnetsV2Out()

    h1_snapshot = (
        compute_liquidity_snapshot(
            symbol=symbol,
            timeframe="H1",
            current_price=payload.current_price,
            candles=h1_candles,
            pdh=levels.pdh,
            pdl=levels.pdl,
        )
        if h1_candles
        else None
    )
    h4_snapshot = (
        compute_liquidity_snapshot(
            symbol=symbol,
            timeframe="H4",
            current_price=payload.current_price,
            candles=h4_candles,
            pdh=levels.pdh,
            pdl=levels.pdl,
        )
        if h4_candles
        else None
    )

    h1_magnets = [
        _liquidity_out(rank=index, timeframe="H1", magnet=magnet)
        for index, magnet in enumerate((h1_snapshot.strong_magnets if h1_snapshot else [])[:3], start=1)
    ]
    h4_magnets = [
        _liquidity_out(rank=index, timeframe="H4", magnet=magnet)
        for index, magnet in enumerate((h4_snapshot.strong_magnets if h4_snapshot else [])[:3], start=1)
    ]

    ranked = _iter_ranked_magnets([*h1_magnets, *h4_magnets])
    strongest = ranked[0] if ranked else None

    biases = [
        snapshot.htf_magnet_bias
        for snapshot in (h1_snapshot, h4_snapshot)
        if snapshot is not None
    ]
    if "bullish" in biases and "bearish" not in biases:
        htf_bias = "bullish"
    elif "bearish" in biases and "bullish" not in biases:
        htf_bias = "bearish"
    else:
        htf_bias = "neutral"

    return LiquidityMagnetsV2Out(
        strongest_magnet=strongest,
        h1_magnets=h1_magnets,
        h4_magnets=h4_magnets,
        htf_magnet_bias=htf_bias,  # type: ignore[arg-type]
    )


def compute_zone_to_zone_path(current_price: float, magnets: LiquidityMagnetsV2Out) -> ZoneToZonePathOut:
    candidates = [*magnets.h1_magnets, *magnets.h4_magnets]
    if not candidates:
        return ZoneToZonePathOut(from_zone=_round_price(current_price))

    above = sorted(
        [magnet for magnet in candidates if magnet.side == "above"],
        key=lambda item: (item.distance, -item.strength),
    )
    below = sorted(
        [magnet for magnet in candidates if magnet.side == "below"],
        key=lambda item: (item.distance, -item.strength),
    )

    strongest = magnets.strongest_magnet
    up_strength = above[0].strength if above else 0
    down_strength = below[0].strength if below else 0

    if strongest is not None:
        direction = "up" if strongest.side == "above" else "down"
    elif up_strength > down_strength:
        direction = "up"
    elif down_strength > up_strength:
        direction = "down"
    else:
        direction = "balanced"

    if direction == "up":
        path_source = above[:2] or _iter_ranked_magnets(candidates)[:2]
    elif direction == "down":
        path_source = below[:2] or _iter_ranked_magnets(candidates)[:2]
    else:
        path_source = _iter_ranked_magnets(candidates)[:2]

    path = [
        ZonePathLevelOut(
            label=f"{item.timeframe} {item.label}",
            price=item.price,
            timeframe=item.timeframe,
            side=item.side,
            strength=item.strength,
        )
        for item in path_source
    ]

    next_zone = path_source[0].price if path_source else None
    major_zone = path_source[1].price if len(path_source) > 1 else next_zone
    if not above and not below:
        direction = "balanced"

    return ZoneToZonePathOut(
        from_zone=_round_price(current_price),
        next_zone=next_zone,
        major_zone=major_zone,
        direction=direction,  # type: ignore[arg-type]
        path=path,
    )


def compute_volatility_state(payload: OracleEvaluateRequest) -> VolatilityStateOut:
    _, adr_state = _compute_daily_context(payload)
    adr_used_pct = round(float(adr_state.adr_used_pct), 2)
    atr = _round_price(payload.atr_m1)

    if adr_used_pct >= 100:
        state = "extreme"
    elif adr_used_pct >= 75:
        state = "high"
    elif adr_used_pct >= 20:
        state = "normal"
    else:
        state = "low"

    return VolatilityStateOut(atr=atr, adr_used_pct=adr_used_pct, state=state)  # type: ignore[arg-type]


def compute_manipulation_zone(
    payload: OracleEvaluateRequest,
    anchor: Anchor0801BiasOut,
    session: str = "london",
) -> ManipulationZoneOut:
    if session.lower() != "london" or not payload.m1_candles:
        return ManipulationZoneOut()

    asian_candles = []
    for candle in payload.m1_candles:
        candle_utc = candle.time.astimezone(UTC)
        london_time = candle_utc + timedelta(hours=london_offset_hours(candle_utc))
        if 0 <= london_time.hour < 8:
            asian_candles.append(candle)

    if not asian_candles:
        return ManipulationZoneOut()

    zone_high = _round_price(max(candle.high for candle in asian_candles))
    zone_low = _round_price(min(candle.low for candle in asian_candles))
    latest_close = payload.m15_candles[-1].close if payload.m15_candles else payload.current_price

    if payload.current_price > zone_high and latest_close < zone_high:
        zone_type = "buy_side_sweep"
        active = True
    elif payload.current_price < zone_low and latest_close > zone_low:
        zone_type = "sell_side_sweep"
        active = True
    elif zone_low <= payload.current_price <= zone_high and anchor.bias == "neutral":
        zone_type = "range_trap"
        active = True
    else:
        zone_type = "none"
        active = False

    return ManipulationZoneOut(
        active=active,
        zone_high=zone_high,
        zone_low=zone_low,
        type=zone_type,  # type: ignore[arg-type]
    )


def compute_m15_midlevel_break(
    payload: OracleEvaluateRequest,
    anchor: Anchor0801BiasOut,
    next_level: float | None = None,
) -> M15MidlevelBreakOut:
    midlevel = anchor.anchor_mid
    if midlevel <= 0 or not payload.m15_candles:
        return M15MidlevelBreakOut(midlevel=midlevel)

    latest_close = _field_value(payload.m15_candles[-1], "close")
    previous_close = _field_value(payload.m15_candles[-2], "close") if len(payload.m15_candles) > 1 else payload.prev_m15_close

    if previous_close <= midlevel < latest_close:
        direction = "break_up"
        confirmed = True
        projected_level = next_level if next_level is not None else max(
            latest_close,
            max(_field_value(candle, "high") for candle in payload.m15_candles[-4:]),
        )
        reason = "M15 closed above midlevel; next upside magnet selected."
    elif previous_close >= midlevel > latest_close:
        direction = "break_down"
        confirmed = True
        projected_level = next_level if next_level is not None else min(
            latest_close,
            min(_field_value(candle, "low") for candle in payload.m15_candles[-4:]),
        )
        reason = "M15 closed below midlevel; next downside magnet selected."
    else:
        direction = "none"
        confirmed = False
        projected_level = next_level or 0.0
        reason = "No confirmed M15 close beyond the anchor midlevel."

    return M15MidlevelBreakOut(
        confirmed=confirmed,
        direction=direction,  # type: ignore[arg-type]
        midlevel=_round_price(midlevel),
        next_level=_round_price(projected_level),
        reason=reason,
    )


def compute_highest_probability_direction(
    anchor_0801: Anchor0801BiasOut,
    discount_premium: DiscountPremiumZoneOut,
    liquidity_magnets: LiquidityMagnetsV2Out,
    zone_to_zone: ZoneToZonePathOut,
    volatility: VolatilityStateOut,
    manipulation_zone: ManipulationZoneOut,
    m15_midlevel_break: M15MidlevelBreakOut,
) -> HighestProbabilityDirectionOut:
    buy_parts = HighestProbabilityScoreBreakdownOut()
    sell_parts = HighestProbabilityScoreBreakdownOut()

    if anchor_0801.bias == "bullish":
        buy_parts.anchor_bias = 24
    elif anchor_0801.bias == "bearish":
        sell_parts.anchor_bias = 24

    if discount_premium.price_position == "discount":
        buy_parts.zone_position = 12
    elif discount_premium.price_position == "premium":
        sell_parts.zone_position = 12
    else:
        buy_parts.zone_position = 3
        sell_parts.zone_position = 3

    if zone_to_zone.direction == "up":
        buy_parts.liquidity_path = 18
    elif zone_to_zone.direction == "down":
        sell_parts.liquidity_path = 18
    else:
        buy_parts.liquidity_path = 4
        sell_parts.liquidity_path = 4

    if volatility.state == "normal":
        buy_parts.volatility = 10
        sell_parts.volatility = 10
    elif volatility.state == "high":
        buy_parts.volatility = 8
        sell_parts.volatility = 8
    elif volatility.state == "low":
        buy_parts.volatility = 3
        sell_parts.volatility = 3

    if manipulation_zone.type == "sell_side_sweep":
        buy_parts.manipulation = 14
    elif manipulation_zone.type == "buy_side_sweep":
        sell_parts.manipulation = 14
    elif manipulation_zone.type == "range_trap":
        buy_parts.manipulation = 4
        sell_parts.manipulation = 4

    if m15_midlevel_break.direction == "break_up" and m15_midlevel_break.confirmed:
        buy_parts.m15_break = 20
    elif m15_midlevel_break.direction == "break_down" and m15_midlevel_break.confirmed:
        sell_parts.m15_break = 20

    buy_score = sum(buy_parts.model_dump().values())
    sell_score = sum(sell_parts.model_dump().values())

    if max(buy_score, sell_score) < 35 or abs(buy_score - sell_score) < 8:
        direction = "wait"
        confidence = min(max(buy_score, sell_score), 55)
        reason = "Directional factors are mixed, so waiting is higher quality than forcing a trade."
        score_breakdown = HighestProbabilityScoreBreakdownOut()
    elif buy_score > sell_score:
        direction = "buy"
        confidence = min(99, buy_score)
        reasons = ["08:01 bias", "discount pricing", "upside liquidity path", "confirmed M15 break"]
        reason = "Bullish alignment across " + ", ".join(
            label for label, points in zip(
                reasons,
                [
                    buy_parts.anchor_bias,
                    buy_parts.zone_position,
                    buy_parts.liquidity_path,
                    buy_parts.m15_break,
                ],
            )
            if points > 0
        ) + "."
        score_breakdown = buy_parts
    else:
        direction = "sell"
        confidence = min(99, sell_score)
        reasons = ["08:01 bias", "premium pricing", "downside liquidity path", "confirmed M15 break"]
        reason = "Bearish alignment across " + ", ".join(
            label for label, points in zip(
                reasons,
                [
                    sell_parts.anchor_bias,
                    sell_parts.zone_position,
                    sell_parts.liquidity_path,
                    sell_parts.m15_break,
                ],
            )
            if points > 0
        ) + "."
        score_breakdown = sell_parts

    return HighestProbabilityDirectionOut(
        direction=direction,  # type: ignore[arg-type]
        confidence=confidence,
        reason=reason,
        score_breakdown=score_breakdown,
    )


def empty_v2_intelligence(symbol: str) -> V2IntelligenceResponse:
    return V2IntelligenceResponse(
        symbol=normalize_symbol(symbol),
        current_price=0.0,
        updated_at=datetime.utcnow(),
    )


def build_v2_intelligence_snapshot(
    payload: OracleEvaluateRequest,
    *,
    news_context: NewsContextOut | None = None,
) -> V2IntelligenceResponse:
    symbol = normalize_symbol(payload.symbol)
    anchor_0801 = compute_0801_bias(payload)
    discount_premium = compute_discount_premium_zone(anchor_0801, payload.current_price)
    liquidity_magnets = compute_h1_h4_liquidity_magnets(payload)
    zone_to_zone = compute_zone_to_zone_path(payload.current_price, liquidity_magnets)
    volatility = compute_volatility_state(payload)
    manipulation_zone = compute_manipulation_zone(payload, anchor_0801)
    m15_midlevel_break = compute_m15_midlevel_break(
        payload,
        anchor_0801,
        next_level=zone_to_zone.next_zone,
    )
    highest_probability_direction = compute_highest_probability_direction(
        anchor_0801,
        discount_premium,
        liquidity_magnets,
        zone_to_zone,
        volatility,
        manipulation_zone,
        m15_midlevel_break,
    )

    return V2IntelligenceResponse(
        symbol=symbol,
        current_price=_round_price(payload.current_price),
        anchor_0801=anchor_0801,
        discount_premium=discount_premium,
        liquidity_magnets=liquidity_magnets,
        zone_to_zone=zone_to_zone,
        volatility=volatility,
        manipulation_zone=manipulation_zone,
        m15_midlevel_break=m15_midlevel_break,
        highest_probability_direction=highest_probability_direction,
        news_context=news_context or NewsContextOut(),
        updated_at=datetime.utcnow(),
    )
