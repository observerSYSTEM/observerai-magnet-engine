from pydantic import BaseModel


class AnchorStateResponse(BaseModel):
    symbol: str
    anchor_time: str
    anchor_open: float
    anchor_high: float
    anchor_low: float
    anchor_close: float
    anchor_direction: str
    anchor_type: str
    premium_low: float
    premium_high: float
    discount_low: float
    discount_high: float
    value_low: float
    value_high: float
    note: str