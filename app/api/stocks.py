from fastapi import APIRouter, Depends

from app.core.rate_limit import rate_limit
from app.schemas.stocks import WeeklyStockOpportunitiesResponse
from app.services.stock_opportunities import scan_weekly_stock_opportunities

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/weekly-opportunities", response_model=WeeklyStockOpportunitiesResponse)
def weekly_stock_opportunities(
    _: None = Depends(rate_limit("stocks_weekly_opportunities", limit=30, window_seconds=60)),
) -> WeeklyStockOpportunitiesResponse:
    return scan_weekly_stock_opportunities()
