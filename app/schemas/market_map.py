from pydantic import BaseModel


class MarketMapOut(BaseModel):
    symbol: str
    pdh: float
    pdl: float
    eq: float
    day_open: float
    adr: float
    adr_high: float
    adr_low: float
    adr_used_pct: float
    anchor_direction: str
    anchor_type: str
    premium_low: float
    premium_high: float
    discount_low: float
    discount_high: float
    value_low: float
    value_high: float
    current_zone: str
    bias: str
