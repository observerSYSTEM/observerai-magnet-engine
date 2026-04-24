from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.symbols import DEFAULT_SYMBOL
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.signal import BestSignalResponse, SignalsLatestResponse
from app.services.best_signal_service import select_best_signal
from app.services.signal_service import list_latest_signals

router = APIRouter(prefix='/signals', tags=['signals'])


@router.get('/latest', response_model=SignalsLatestResponse)
def latest_signals(
    symbol: str = DEFAULT_SYMBOL,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    _: None = Depends(rate_limit("signals_latest", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
):
    return list_latest_signals(db, symbol, limit)


@router.get('/best', response_model=BestSignalResponse)
def best_signal(
    _: None = Depends(rate_limit("signals_best", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
):
    return select_best_signal(db)
