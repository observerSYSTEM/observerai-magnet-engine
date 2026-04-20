from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.signal_outcome import SignalOutcome


class Signal(Base):
    __tablename__ = 'signals'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    direction: Mapped[str] = mapped_column(String(20))
    trigger_level_name: Mapped[str] = mapped_column(String(50))
    trigger_level_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    nearest_magnet_name: Mapped[str] = mapped_column(String(50))
    nearest_magnet_price: Mapped[float] = mapped_column(Float)
    major_magnet_name: Mapped[str] = mapped_column(String(50))
    major_magnet_price: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    bias: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolved_bias: Mapped[str | None] = mapped_column(String(50), nullable=True)
    anchor_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    anchor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    adr: Mapped[float | None] = mapped_column(Float, nullable=True)
    adr_used_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    adr_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nearest_magnet: Mapped[str | None] = mapped_column(Text, nullable=True)
    major_magnet: Mapped[str | None] = mapped_column(Text, nullable=True)
    magnet_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    sweep: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure: Mapped[str | None] = mapped_column(Text, nullable=True)
    momentum: Mapped[str | None] = mapped_column(Text, nullable=True)
    mid_targets: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    outcome: Mapped["SignalOutcome | None"] = relationship(
        back_populates="signal",
        uselist=False,
        cascade="all, delete-orphan",
    )
