from datetime import datetime

from pydantic import BaseModel, Field


class CandleIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    timeframe: str = Field(min_length=1, max_length=10)
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
