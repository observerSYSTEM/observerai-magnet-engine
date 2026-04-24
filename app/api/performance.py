from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.symbols import DEFAULT_SYMBOL
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.performance import PerformanceSignalsResponse, PerformanceSummaryResponse
from app.services.performance_service import get_performance_summary, list_performance_signals

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary", response_model=PerformanceSummaryResponse)
def performance_summary(
    symbol: str = DEFAULT_SYMBOL,
    _: None = Depends(rate_limit("performance_summary", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> PerformanceSummaryResponse:
    return get_performance_summary(db, symbol=symbol)


@router.get("/signals", response_model=PerformanceSignalsResponse)
def performance_signals(
    symbol: str = DEFAULT_SYMBOL,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    _: None = Depends(rate_limit("performance_signals", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> PerformanceSignalsResponse:
    return list_performance_signals(db, symbol=symbol, limit=limit)
