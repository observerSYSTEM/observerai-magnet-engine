from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.signal import Signal


class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    action: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_hint: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    mfe: Mapped[float] = mapped_column(Float, default=0.0)
    mae: Mapped[float] = mapped_column(Float, default=0.0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signal: Mapped["Signal"] = relationship(back_populates="outcome")
