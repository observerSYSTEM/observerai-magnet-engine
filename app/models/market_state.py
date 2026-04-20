from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MarketState(Base):
    __tablename__ = 'market_state'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    pdh: Mapped[float] = mapped_column(Float)
    pdl: Mapped[float] = mapped_column(Float)
    eq: Mapped[float] = mapped_column(Float)
    day_open: Mapped[float] = mapped_column(Float)
    adr: Mapped[float] = mapped_column(Float)
    adr_high: Mapped[float] = mapped_column(Float)
    adr_low: Mapped[float] = mapped_column(Float)
    adr_used_pct: Mapped[float] = mapped_column(Float)
    anchor_direction: Mapped[str] = mapped_column(String(20), default='neutral')
    anchor_type: Mapped[str] = mapped_column(String(20), default='neutral')
    premium_low: Mapped[float] = mapped_column(Float, default=0)
    premium_high: Mapped[float] = mapped_column(Float, default=0)
    discount_low: Mapped[float] = mapped_column(Float, default=0)
    discount_high: Mapped[float] = mapped_column(Float, default=0)
    value_low: Mapped[float] = mapped_column(Float, default=0)
    value_high: Mapped[float] = mapped_column(Float, default=0)
    current_zone: Mapped[str] = mapped_column(String(50), default='neutral')
    bias: Mapped[str] = mapped_column(String(20), default='neutral')
