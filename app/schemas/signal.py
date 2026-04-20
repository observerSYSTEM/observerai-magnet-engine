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
    confidence: int
    message: str
    created_at: datetime


class SignalsLatestResponse(BaseModel):
    symbol: str
    count: int
    items: list[StoredSignalOut]
