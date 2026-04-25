from __future__ import annotations

from pydantic import BaseModel, Field


class WeeklyStockOpportunityOut(BaseModel):
    symbol: str
    bias: str
    confidence: int
    setup_type: str
    entry_zone: str
    target_zone: str
    risk_note: str
    reason: str


class WeeklyStockOpportunitiesResponse(BaseModel):
    week: str
    available: bool = True
    message: str | None = None
    opportunities: list[WeeklyStockOpportunityOut] = Field(default_factory=list)
