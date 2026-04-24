from fastapi import APIRouter

from app.core.symbols import DEFAULT_SYMBOL, normalize_symbol

router = APIRouter(prefix='/market-map', tags=['market-map'])


@router.get('')
def market_map(symbol: str = DEFAULT_SYMBOL):
    return {
        'symbol': normalize_symbol(symbol),
        'note': 'Connect this route to stored market_state rows next.',
    }
