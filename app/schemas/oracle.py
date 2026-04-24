from typing import Literal, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OracleTimedCandleIn(BaseModel):
    """Timestamped OHLC candle used for intraday inputs."""

    model_config = ConfigDict(extra="forbid")

    time: AwareDatetime
    open: float
    high: float
    low: float
    close: float


class OraclePriceCandleIn(BaseModel):
    """OHLC candle used for M15 and daily inputs."""

    model_config = ConfigDict(extra="forbid")

    time: str = Field(min_length=1, max_length=64)
    open: float
    high: float
    low: float
    close: float


class OracleEvaluateRequest(BaseModel):
    """Request payload for real-time oracle evaluation."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=20)
    current_price: float
    prev_m15_close: float
    m1_candles: list[OracleTimedCandleIn] = Field(min_length=1, max_length=2000)
    m15_candles: list[OraclePriceCandleIn] = Field(min_length=1, max_length=500)
    h1_candles: list[OraclePriceCandleIn] | None = Field(default=None, max_length=1000)
    h4_candles: list[OraclePriceCandleIn] | None = Field(default=None, max_length=500)
    daily_candles_for_levels: list[OraclePriceCandleIn] = Field(min_length=2, max_length=10)
    daily_candles_for_adr: list[OraclePriceCandleIn] = Field(min_length=5, max_length=30)
    atr_m1: float = Field(gt=0)


class MagnetInfo(BaseModel):
    name: str
    price: float
    direction: str
    strength: float
    source: str
    rank_score: float | None = None
    distance: float | None = None


class SweepOut(BaseModel):
    type: Literal["none", "buyside", "sellside"]
    strength: float


class StructureOut(BaseModel):
    type: Literal["none", "bos", "mss"]
    direction: Literal["neutral", "bullish", "bearish"]


class MomentumOut(BaseModel):
    direction: Literal["neutral", "bullish", "bearish"]
    body_ratio: float
    wick_ratio: float
    classification: Literal["weak", "moderate", "strong"]


class MidPointOut(BaseModel):
    name: str
    price: float


class MidTargetsOut(BaseModel):
    current_mid: Optional[MidPointOut] = None
    next_mid: Optional[MidPointOut] = None
    flow: Literal[
        "bullish_mid_to_mid",
        "bearish_mid_to_mid",
        "mid_compression",
        "no_mid_flow",
    ]


class IntentOut(BaseModel):
    action: Literal["BUY", "SELL", "WAIT"]
    entry_type: Literal["continuation", "reversal", "none"]
    reason: str
    target: Optional[float] = None
    stop_hint: Optional[str] = None


class OracleEvaluateResponse(BaseModel):
    symbol: str
    current_price: float
    bias: str
    resolved_bias: str
    event_type: str
    anchor_direction: str
    anchor_type: str
    anchor_note: str
    adr: float
    adr_used_pct: float
    adr_state: str
    nearest_magnet: Optional[MagnetInfo] = None
    major_magnet: Optional[MagnetInfo] = None
    magnet_path: list[MagnetInfo] = Field(default_factory=list)
    sweep: Optional[SweepOut] = None
    structure: Optional[StructureOut] = None
    momentum: Optional[MomentumOut] = None
    mid_targets: Optional[MidTargetsOut] = None
    intent: IntentOut
    confidence: int
    message: str
