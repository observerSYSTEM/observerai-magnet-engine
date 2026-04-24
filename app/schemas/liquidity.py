from typing import Literal

from pydantic import BaseModel, Field


class LiquidityMagnetOut(BaseModel):
    rank: int
    type: str
    label: str
    price: float
    side: Literal["above", "below"]
    distance: float
    strength: int
    reason: str


class LiquidityMagnetsResponse(BaseModel):
    symbol: str
    timeframe: Literal["H1", "H4"]
    current_price: float
    strong_magnets: list[LiquidityMagnetOut] = Field(default_factory=list)
    htf_magnet_bias: Literal["bullish", "bearish", "neutral"] = "neutral"
