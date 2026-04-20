from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.audit import require_admin_access
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.signal import SignalsLatestResponse
from app.services.signal_service import list_latest_signals

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get(
    "/status",
    dependencies=[Depends(rate_limit("admin_status", limit=30, window_seconds=60))],
)
def admin_status(current_user: User = Depends(require_admin_access)) -> dict[str, object]:
    return {
        "status": "ok",
        "email": current_user.email,
        "role": current_user.role,
    }


@router.get(
    "/runner/status",
    dependencies=[Depends(rate_limit("admin_runner_status", limit=30, window_seconds=60))],
)
def admin_runner_status(
    _: User = Depends(require_admin_access),
) -> dict[str, object]:
    settings = get_settings()
    return {
        "default_symbol": settings.default_symbol,
        "mt5_configured": bool(
            settings.mt5_login is not None
            and settings.mt5_server
            and settings.mt5_terminal_path
        ),
        "telegram_alerts_enabled": settings.telegram_alerts_enabled,
    }


@router.get(
    "/signals/latest",
    response_model=SignalsLatestResponse,
    dependencies=[Depends(rate_limit("admin_signals_latest", limit=60, window_seconds=60))],
)
def admin_latest_signals(
    symbol: str = "XAUUSD",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    _: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
) -> SignalsLatestResponse:
    return list_latest_signals(db, symbol, limit)
