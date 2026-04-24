from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.core.symbols import DEFAULT_SYMBOL, normalize_symbol
from app.db.session import get_db
from app.schemas.liquidity import LiquidityMagnetsResponse
from app.services.market_state_service import get_liquidity_magnets

router = APIRouter(prefix="/liquidity", tags=["liquidity"])


@router.get("/magnets", response_model=LiquidityMagnetsResponse)
def liquidity_magnets(
    symbol: str = DEFAULT_SYMBOL,
    timeframe: Literal["H1", "H4"] = "H1",
    _: None = Depends(rate_limit("liquidity_magnets", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> LiquidityMagnetsResponse:
    return get_liquidity_magnets(
        db,
        symbol=normalize_symbol(symbol),
        timeframe=timeframe,
    )
