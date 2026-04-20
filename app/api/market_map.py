from fastapi import APIRouter

router = APIRouter(prefix='/market-map', tags=['market-map'])


@router.get('')
def market_map(symbol: str = 'XAUUSD'):
    return {
        'symbol': symbol,
        'note': 'Connect this route to stored market_state rows next.',
    }
