from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.oracle import (
    IntentOut,
    MagnetInfo,
    MidTargetsOut,
    MomentumOut,
    StructureOut,
    SweepOut,
)
from app.schemas.v2 import HtfContextOut


class SignalLifecycleOut(BaseModel):
    state: str
    outcome_status: str
    tracking_enabled: bool
    target_hit: bool
    invalidated: bool
    expired: bool
    closed_at: datetime | None = None


class StoredSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    current_price: float
    bias: str
    resolved_bias: str
    event_type: str
    anchor_direction: str
    anchor_type: str
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
    lifecycle: SignalLifecycleOut
    confidence: int
    message: str
    created_at: datetime


class SignalsLatestResponse(BaseModel):
    symbol: str
    count: int
    items: list[StoredSignalOut]


class LatestSignalResponse(BaseModel):
    symbol: str
    item: Optional[StoredSignalOut] = None


class EaLatestSignalResponse(BaseModel):
    symbol: str
    action: Optional[str] = None
    bias: Optional[str] = None
    confidence: Optional[int] = None
    price: Optional[float] = None
    target: Optional[float] = None
    stop_hint: Optional[str] = None
    nearest_magnet: Optional[str] = None
    major_magnet: Optional[str] = None
    tradeable: bool
    lifecycle: Optional[str] = None
    htf_context: HtfContextOut | None = None
    created_at: datetime | None = None
    message: Optional[str] = None


class BestSignalResponse(BaseModel):
    symbol: Optional[str] = None
    action: Optional[str] = None
    bias: Optional[str] = None
    confidence: Optional[int] = None
    price: Optional[float] = None
    target: Optional[float] = None
    tradeable: bool
    reason: Optional[str] = None
    message: Optional[str] = None
