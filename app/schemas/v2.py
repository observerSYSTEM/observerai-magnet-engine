from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class V2LiquidityMagnetOut(BaseModel):
    rank: int
    timeframe: Literal["H1", "H4"]
    type: str
    label: str
    price: float
    side: Literal["above", "below"]
    distance: float
    strength: int
    reason: str


class ZonePathLevelOut(BaseModel):
    label: str
    price: float
    timeframe: Literal["H1", "H4"] | None = None
    side: Literal["above", "below"] | None = None
    strength: int | None = None


class Anchor0801BiasOut(BaseModel):
    anchor_time: str = "08:01"
    anchor_high: float = 0.0
    anchor_low: float = 0.0
    anchor_mid: float = 0.0
    anchor_type: Literal["wick_rejection", "body_acceptance", "neutral"] = "neutral"
    bias: Literal["bullish", "bearish", "neutral"] = "neutral"
    reason: str = "08:01 London anchor is unavailable."


class DiscountPremiumZoneOut(BaseModel):
    premium_high: float = 0.0
    discount_low: float = 0.0
    midlevel: float = 0.0
    price_position: Literal["premium", "discount", "mid"] = "mid"


class LiquidityMagnetsV2Out(BaseModel):
    strongest_magnet: V2LiquidityMagnetOut | None = None
    h1_magnets: list[V2LiquidityMagnetOut] = Field(default_factory=list)
    h4_magnets: list[V2LiquidityMagnetOut] = Field(default_factory=list)
    htf_magnet_bias: Literal["bullish", "bearish", "neutral"] = "neutral"


class ZoneToZonePathOut(BaseModel):
    from_zone: float = 0.0
    next_zone: float | None = None
    major_zone: float | None = None
    direction: Literal["up", "down", "balanced"] = "balanced"
    path: list[ZonePathLevelOut] = Field(default_factory=list)


class VolatilityStateOut(BaseModel):
    atr: float = 0.0
    adr_used_pct: float = 0.0
    state: Literal["low", "normal", "high", "extreme"] = "low"


class ManipulationZoneOut(BaseModel):
    active: bool = False
    zone_high: float = 0.0
    zone_low: float = 0.0
    type: Literal["buy_side_sweep", "sell_side_sweep", "range_trap", "none"] = "none"


class M15MidlevelBreakOut(BaseModel):
    confirmed: bool = False
    direction: Literal["break_up", "break_down", "none"] = "none"
    midlevel: float = 0.0
    next_level: float = 0.0
    reason: str = "No confirmed M15 midlevel break."


class HighestProbabilityScoreBreakdownOut(BaseModel):
    anchor_bias: int = 0
    zone_position: int = 0
    liquidity_path: int = 0
    volatility: int = 0
    manipulation: int = 0
    m15_break: int = 0


class HighestProbabilityDirectionOut(BaseModel):
    direction: Literal["buy", "sell", "wait"] = "wait"
    confidence: int = 0
    reason: str = "No strong directional alignment yet."
    score_breakdown: HighestProbabilityScoreBreakdownOut = Field(
        default_factory=HighestProbabilityScoreBreakdownOut
    )


class NewsContextOut(BaseModel):
    has_high_impact_news: bool = False
    event: str | None = None
    currency: str | None = None
    time: datetime | None = None
    impact: str = "none"
    expected_direction: str = "neutral"
    trade_policy: str = "normal"


class HtfContextOut(BaseModel):
    bias: Literal["bullish", "bearish", "neutral"] = "neutral"
    strongest_magnet: float | None = None
    alignment: Literal["aligned", "against", "mixed"] = "mixed"


class V2IntelligenceResponse(BaseModel):
    symbol: str
    current_price: float
    anchor_0801: Anchor0801BiasOut = Field(default_factory=Anchor0801BiasOut)
    discount_premium: DiscountPremiumZoneOut = Field(default_factory=DiscountPremiumZoneOut)
    liquidity_magnets: LiquidityMagnetsV2Out = Field(default_factory=LiquidityMagnetsV2Out)
    zone_to_zone: ZoneToZonePathOut = Field(default_factory=ZoneToZonePathOut)
    volatility: VolatilityStateOut = Field(default_factory=VolatilityStateOut)
    manipulation_zone: ManipulationZoneOut = Field(default_factory=ManipulationZoneOut)
    m15_midlevel_break: M15MidlevelBreakOut = Field(default_factory=M15MidlevelBreakOut)
    highest_probability_direction: HighestProbabilityDirectionOut = Field(
        default_factory=HighestProbabilityDirectionOut
    )
    news_context: NewsContextOut = Field(default_factory=NewsContextOut)
    updated_at: datetime


class DashboardScalpSignalOut(BaseModel):
    action: str | None = None
    bias: str | None = None
    confidence: int | None = None
    target: float | None = None
    lifecycle: str | None = None
    tradeable: bool = False
    created_at: datetime | None = None


class V2DashboardSymbolSummaryOut(BaseModel):
    symbol: str
    current_price: float
    anchor_bias: Literal["bullish", "bearish", "neutral"] = "neutral"
    strongest_h1_magnet: V2LiquidityMagnetOut | None = None
    strongest_h4_magnet: V2LiquidityMagnetOut | None = None
    strongest_magnet: V2LiquidityMagnetOut | None = None
    zone_to_zone: ZoneToZonePathOut = Field(default_factory=ZoneToZonePathOut)
    volatility_state: Literal["low", "normal", "high", "extreme"] = "low"
    highest_probability_direction: HighestProbabilityDirectionOut = Field(
        default_factory=HighestProbabilityDirectionOut
    )
    news_context: NewsContextOut = Field(default_factory=NewsContextOut)
    scalp_signal: DashboardScalpSignalOut | None = None


class BestDirectionNowOut(BaseModel):
    symbol: str | None = None
    current_price: float | None = None
    confidence: int = 0
    direction: Literal["buy", "sell", "wait"] = "wait"
    anchor_bias: Literal["bullish", "bearish", "neutral"] = "neutral"
    trade_policy: str = "normal"


class V2DashboardSummaryResponse(BaseModel):
    updated_at: datetime
    best_direction_now: BestDirectionNowOut | None = None
    symbols: list[V2DashboardSymbolSummaryOut] = Field(default_factory=list)
