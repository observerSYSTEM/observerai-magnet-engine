from datetime import datetime, timedelta
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.candle import Candle

init_db()
db = SessionLocal()
base = datetime.utcnow() - timedelta(hours=5)
for i in range(20):
    px = 2400 + i * 0.8
    db.add(Candle(symbol='XAUUSD', timeframe='M15', time=base + timedelta(minutes=15 * i), open=px, high=px+1.2, low=px-0.6, close=px+0.4, volume=100+i))
db.commit()
db.close()
print('Seeded sample candles.')
