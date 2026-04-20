from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.audit import require_admin_access
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.candle import CandleIn
from app.services.candle_service import save_candle

router = APIRouter(prefix='/ingest', tags=['ingest'])


@router.post('/mt5/candle')
def ingest_candle(
    payload: CandleIn,
    _: User = Depends(require_admin_access),
    __: None = Depends(rate_limit("ingest_mt5_candle", limit=120, window_seconds=60)),
    db: Session = Depends(get_db),
):
    row = save_candle(db, payload)
    return {'status': 'ok', 'id': row.id}
