from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.oracle import evaluate_oracle_post
from app.api.performance import performance_signals, performance_summary
from app.db.base import Base
from app.schemas.oracle import OracleEvaluateRequest
from app.services.performance_service import evaluate_open_signal_outcomes


def _sample_oracle_request(current_price: float = 3358.40) -> OracleEvaluateRequest:
    return OracleEvaluateRequest(
        symbol="XAUUSD",
        current_price=current_price,
        prev_m15_close=3350.10,
        m1_candles=[
            {
                "time": "2026-04-19T06:59:00Z",
                "open": 3347.20,
                "high": 3348.00,
                "low": 3346.90,
                "close": 3347.80,
            },
            {
                "time": "2026-04-19T07:00:00Z",
                "open": 3347.80,
                "high": 3348.10,
                "low": 3347.40,
                "close": 3347.95,
            },
            {
                "time": "2026-04-19T07:01:00Z",
                "open": 3348.20,
                "high": 3351.10,
                "low": 3346.80,
                "close": 3350.40,
            },
            {
                "time": "2026-04-19T07:02:00Z",
                "open": 3350.40,
                "high": 3350.70,
                "low": 3349.90,
                "close": 3350.10,
            },
        ],
        m15_candles=[
            {"time": "2026-04-19T10:00:00", "open": 3346.0, "high": 3349.0, "low": 3344.8, "close": 3348.5},
            {"time": "2026-04-19T10:15:00", "open": 3348.5, "high": 3350.5, "low": 3347.9, "close": 3350.1},
            {"time": "2026-04-19T10:30:00", "open": 3350.1, "high": 3352.4, "low": 3349.6, "close": 3351.8},
            {"time": "2026-04-19T10:45:00", "open": 3351.8, "high": 3354.0, "low": 3351.2, "close": 3353.2},
            {"time": "2026-04-19T11:00:00", "open": 3353.2, "high": 3355.8, "low": 3352.8, "close": 3354.9},
            {"time": "2026-04-19T11:15:00", "open": 3354.9, "high": 3357.2, "low": 3354.4, "close": 3356.3},
            {"time": "2026-04-19T11:30:00", "open": 3356.3, "high": max(3359.1, current_price), "low": 3355.8, "close": current_price},
        ],
        daily_candles_for_levels=[
            {"time": "2026-04-19", "open": 3348.20, "high": 3360.00, "low": 3344.00, "close": current_price},
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
    db_path = db_dir / f"observerai-performance-{uuid4().hex}.db"
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


def test_oracle_post_creates_signal_outcome_and_performance_list_returns_it():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            payload = performance_signals(symbol="XAUUSD", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert payload["count"] == 1
    assert payload["items"][0]["symbol"] == "XAUUSD"
    assert payload["items"][0]["action"] == "BUY"
    assert payload["items"][0]["entry_price"] == 3358.4
    assert payload["items"][0]["target"] == 3361.4
    assert payload["items"][0]["stop_hint"] == "below_value_low"
    assert payload["items"][0]["outcome_status"] == "open"


def test_performance_summary_counts_target_hit_after_price_update():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            evaluate_open_signal_outcomes(
                db,
                symbol="XAUUSD",
                current_price=3361.40,
            )
            summary = performance_summary(symbol="XAUUSD", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert summary["symbol"] == "XAUUSD"
    assert summary["total_signals"] == 1
    assert summary["open_signals"] == 0
    assert summary["closed_signals"] == 1
    assert summary["target_hit"] == 1
    assert summary["invalidated"] == 0
    assert summary["expired"] == 0
    assert summary["win_rate_pct"] == 100.0


def test_performance_summary_returns_zero_state_for_symbol_without_outcomes():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            summary = performance_summary(symbol="GBPJPY", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert summary["symbol"] == "GBPJPY"
    assert summary["total_signals"] == 0
    assert summary["open_signals"] == 0
    assert summary["closed_signals"] == 0
    assert summary["target_hit"] == 0
    assert summary["invalidated"] == 0
    assert summary["expired"] == 0
    assert summary["win_rate_pct"] == 0.0
