from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.candle import Candle
from app.schemas.candle import CandleIn


def save_candle(db: Session, payload: CandleIn) -> Candle:
    row = Candle(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def latest_candles(db: Session, symbol: str, timeframe: str, limit: int = 20) -> list[Candle]:
    stmt = (
        select(Candle)
        .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
        .order_by(Candle.time.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
