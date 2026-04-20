from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


OutcomeStatus = Literal["open", "target_hit", "invalidated", "expired"]


class StoredSignalOutcomeOut(BaseModel):
    signal_id: int
    symbol: str
    action: Literal["BUY", "SELL", "WAIT"]
    entry_price: float
    target: float | None
    stop_hint: str | None
    outcome_status: OutcomeStatus
    mfe: float
    mae: float
    closed_at: datetime | None


class PerformanceSignalsResponse(BaseModel):
    symbol: str
    count: int
    items: list[StoredSignalOutcomeOut]


class PerformanceSummaryResponse(BaseModel):
    symbol: str
    total_signals: int
    open_signals: int
    closed_signals: int
    target_hit: int
    invalidated: int
    expired: int
    win_rate_pct: float
    avg_mfe: float
    avg_mae: float
