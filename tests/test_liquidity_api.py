from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.liquidity import liquidity_magnets
from app.api.oracle import evaluate_oracle_post
from app.db.base import Base
from app.schemas.oracle import OracleEvaluateRequest


def _sample_oracle_request() -> OracleEvaluateRequest:
    return OracleEvaluateRequest(
        symbol="XAUUSD",
        current_price=3358.40,
        prev_m15_close=3350.10,
        m1_candles=[
            {"time": "2026-04-19T06:59:00Z", "open": 3347.20, "high": 3348.00, "low": 3346.90, "close": 3347.80},
            {"time": "2026-04-19T07:00:00Z", "open": 3347.80, "high": 3348.10, "low": 3347.40, "close": 3347.95},
            {"time": "2026-04-19T07:01:00Z", "open": 3348.20, "high": 3351.10, "low": 3346.80, "close": 3350.40},
            {"time": "2026-04-19T07:02:00Z", "open": 3350.40, "high": 3350.70, "low": 3349.90, "close": 3350.10},
        ],
        m15_candles=[
            {"time": "2026-04-19T10:00:00", "open": 3346.0, "high": 3349.0, "low": 3344.8, "close": 3348.5},
            {"time": "2026-04-19T10:15:00", "open": 3348.5, "high": 3350.5, "low": 3347.9, "close": 3350.1},
            {"time": "2026-04-19T10:30:00", "open": 3350.1, "high": 3352.4, "low": 3349.6, "close": 3351.8},
            {"time": "2026-04-19T10:45:00", "open": 3351.8, "high": 3354.0, "low": 3351.2, "close": 3353.2},
            {"time": "2026-04-19T11:00:00", "open": 3353.2, "high": 3355.8, "low": 3352.8, "close": 3354.9},
            {"time": "2026-04-19T11:15:00", "open": 3354.9, "high": 3357.2, "low": 3354.4, "close": 3356.3},
            {"time": "2026-04-19T11:30:00", "open": 3356.3, "high": 3359.1, "low": 3355.8, "close": 3358.4},
        ],
        h1_candles=[
            {"time": "2026-04-18T00:00:00Z", "open": 3348.0, "high": 3366.80, "low": 3348.0, "close": 3356.2},
            {"time": "2026-04-18T01:00:00Z", "open": 3356.2, "high": 3366.62, "low": 3352.8, "close": 3360.1},
            {"time": "2026-04-18T02:00:00Z", "open": 3360.1, "high": 3364.4, "low": 3346.5, "close": 3348.9},
            {"time": "2026-04-18T03:00:00Z", "open": 3348.9, "high": 3359.2, "low": 3344.12, "close": 3352.4},
            {"time": "2026-04-18T04:00:00Z", "open": 3352.4, "high": 3366.75, "low": 3349.6, "close": 3362.0},
            {"time": "2026-04-18T05:00:00Z", "open": 3362.0, "high": 3365.8, "low": 3357.9, "close": 3361.2},
            {"time": "2026-04-18T06:00:00Z", "open": 3361.2, "high": 3363.1, "low": 3358.3, "close": 3359.4},
            {"time": "2026-04-18T07:00:00Z", "open": 3359.4, "high": 3360.2, "low": 3354.9, "close": 3358.4},
        ],
        h4_candles=[
            {"time": "2026-04-15T00:00:00Z", "open": 3334.0, "high": 3378.9, "low": 3328.6, "close": 3368.4},
            {"time": "2026-04-15T04:00:00Z", "open": 3368.4, "high": 3376.8, "low": 3356.2, "close": 3360.8},
            {"time": "2026-04-15T08:00:00Z", "open": 3360.8, "high": 3378.7, "low": 3349.4, "close": 3352.6},
            {"time": "2026-04-15T12:00:00Z", "open": 3352.6, "high": 3368.1, "low": 3340.2, "close": 3344.6},
            {"time": "2026-04-15T16:00:00Z", "open": 3344.6, "high": 3358.6, "low": 3339.8, "close": 3350.0},
            {"time": "2026-04-15T20:00:00Z", "open": 3350.0, "high": 3364.4, "low": 3344.2, "close": 3358.4},
        ],
        daily_candles_for_levels=[
            {"time": "2026-04-19", "open": 3348.20, "high": 3360.00, "low": 3344.00, "close": 3358.40},
            {"time": "2026-04-18", "open": 3331.00, "high": 3361.40, "low": 3329.80, "close": 3348.00},
        ],
        daily_candles_for_adr=[
            {"time": "2026-04-18", "open": 3331.00, "high": 3361.40, "low": 3329.80, "close": 3348.00},
            {"time": "2026-04-17", "open": 3318.00, "high": 3348.20, "low": 3310.00, "close": 3330.00},
            {"time": "2026-04-16", "open": 3348.00, "high": 3368.00, "low": 3335.00, "close": 3320.00},
            {"time": "2026-04-15", "open": 3302.00, "high": 3334.00, "low": 3296.00, "close": 3318.00},
            {"time": "2026-04-14", "open": 3280.00, "high": 3315.00, "low": 3279.00, "close": 3301.00},
        ],
        atr_m1=1.10,
    )


def _build_test_db():
    db_dir = Path("F:/observerai-magnet-engine/.tmp-test-dbs")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"observerai-liquidity-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return db_path, engine, testing_session_local


def _cleanup_test_db(db_path: Path, engine) -> None:
    engine.dispose()
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


def test_liquidity_route_returns_ranked_h1_and_h4_magnets():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            h1_payload = liquidity_magnets(symbol="XAUUSD", timeframe="H1", db=db).model_dump()
            h4_payload = liquidity_magnets(symbol="XAUUSD", timeframe="H4", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert h1_payload["symbol"] == "XAUUSD"
    assert h1_payload["timeframe"] == "H1"
    assert h1_payload["current_price"] == 3358.4
    assert h1_payload["strong_magnets"]
    assert h1_payload["strong_magnets"][0]["rank"] == 1
    assert h1_payload["strong_magnets"][0]["type"] in {
        "equal_highs",
        "equal_lows",
        "weekly_high",
        "weekly_low",
        "previous_day_high",
        "previous_day_low",
        "round_number",
        "imbalance",
    }
    assert h1_payload["htf_magnet_bias"] in {"bullish", "bearish", "neutral"}

    assert h4_payload["symbol"] == "XAUUSD"
    assert h4_payload["timeframe"] == "H4"
    assert h4_payload["strong_magnets"]
    assert h4_payload["strong_magnets"][0]["rank"] == 1
    assert h4_payload["strong_magnets"][0]["strength"] >= h1_payload["strong_magnets"][0]["strength"] - 20
