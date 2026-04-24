import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.symbols import DEFAULT_SYMBOL
from app.db.session import get_db
from app.schemas.signal import BestSignalResponse, EaLatestSignalResponse
from app.services.best_signal_service import get_latest_ea_signal, select_best_signal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ea", tags=["ea"])


def require_ea_api_key(
    request: Request,
    x_ea_api_key: Annotated[str | None, Header(alias="X-EA-API-Key")] = None,
) -> None:
    settings = get_settings()
    symbol = request.query_params.get("symbol", DEFAULT_SYMBOL)

    if not settings.ea_api_key:
        logger.info("EA request accepted | path=%s symbol=%s auth=disabled", request.url.path, symbol)
        return

    if not x_ea_api_key or not secrets.compare_digest(x_ea_api_key, settings.ea_api_key):
        logger.warning(
            "EA request blocked | path=%s symbol=%s ip=%s",
            request.url.path,
            symbol,
            request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EA access requires a valid Elite API key.",
        )

    logger.info("EA request accepted | path=%s symbol=%s", request.url.path, symbol)


@router.get("/latest-signal", response_model=EaLatestSignalResponse)
def ea_latest_signal(
    symbol: str = DEFAULT_SYMBOL,
    _: None = Depends(require_ea_api_key),
    __: None = Depends(rate_limit("signals_ea_latest", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> EaLatestSignalResponse:
    return get_latest_ea_signal(db, symbol)


@router.get("/best-signal", response_model=BestSignalResponse)
def ea_best_signal(
    _: None = Depends(require_ea_api_key),
    __: None = Depends(rate_limit("signals_ea_best", limit=60, window_seconds=60)),
    db: Session = Depends(get_db),
) -> BestSignalResponse:
    return select_best_signal(db)
