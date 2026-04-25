from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.api.ea import ea_best_signal, ea_latest_signal, require_ea_api_key
from app.api.oracle import evaluate_oracle, evaluate_oracle_post
from app.api.signals import best_signal
from app.core.config import get_settings
from app.db.base import Base
from app.schemas.oracle import OracleEvaluateRequest
from app.services.signal_service import save_evaluated_signal


def _sample_oracle_request(symbol: str, current_price: float) -> OracleEvaluateRequest:
    return OracleEvaluateRequest(
        symbol=symbol,
        current_price=current_price,
        prev_m15_close=current_price - 8.3,
        m1_candles=[
            {
                "time": "2026-04-19T06:59:00Z",
                "open": current_price - 10.2,
                "high": current_price - 9.6,
                "low": current_price - 10.4,
                "close": current_price - 9.9,
            },
            {
                "time": "2026-04-19T07:00:00Z",
                "open": current_price - 9.9,
                "high": current_price - 9.5,
                "low": current_price - 10.1,
                "close": current_price - 9.7,
            },
            {
                "time": "2026-04-19T07:01:00Z",
                "open": current_price - 9.2,
                "high": current_price - 6.0,
                "low": current_price - 10.6,
                "close": current_price - 7.8,
            },
            {
                "time": "2026-04-19T07:02:00Z",
                "open": current_price - 7.8,
                "high": current_price - 7.2,
                "low": current_price - 8.0,
                "close": current_price - 7.5,
            },
        ],
        m15_candles=[
            {"time": "2026-04-19T10:00:00", "open": current_price - 12.0, "high": current_price - 9.0, "low": current_price - 13.2, "close": current_price - 10.5},
            {"time": "2026-04-19T10:15:00", "open": current_price - 10.5, "high": current_price - 8.4, "low": current_price - 11.1, "close": current_price - 8.8},
            {"time": "2026-04-19T10:30:00", "open": current_price - 8.8, "high": current_price - 6.7, "low": current_price - 9.5, "close": current_price - 7.0},
            {"time": "2026-04-19T10:45:00", "open": current_price - 7.0, "high": current_price - 4.8, "low": current_price - 7.4, "close": current_price - 5.1},
            {"time": "2026-04-19T11:00:00", "open": current_price - 5.1, "high": current_price - 2.9, "low": current_price - 5.5, "close": current_price - 3.0},
            {"time": "2026-04-19T11:15:00", "open": current_price - 3.0, "high": current_price - 1.1, "low": current_price - 3.5, "close": current_price - 1.0},
            {"time": "2026-04-19T11:30:00", "open": current_price - 1.0, "high": current_price + 0.7, "low": current_price - 1.4, "close": current_price},
        ],
        daily_candles_for_levels=[
            {"time": "2026-04-19", "open": current_price - 9.2, "high": current_price + 1.2, "low": current_price - 14.4, "close": current_price},
            {"time": "2026-04-18", "open": current_price - 23.0, "high": current_price + 3.4, "low": current_price - 24.2, "close": current_price - 8.6},
        ],
        daily_candles_for_adr=[
            {"time": "2026-04-18", "open": current_price - 23.0, "high": current_price + 3.4, "low": current_price - 24.2, "close": current_price - 8.6},
            {"time": "2026-04-17", "open": current_price - 31.0, "high": current_price - 4.2, "low": current_price - 37.8, "close": current_price - 22.2},
            {"time": "2026-04-16", "open": current_price - 19.0, "high": current_price + 5.8, "low": current_price - 27.2, "close": current_price - 20.8},
            {"time": "2026-04-15", "open": current_price - 44.0, "high": current_price - 13.2, "low": current_price - 49.0, "close": current_price - 31.6},
            {"time": "2026-04-14", "open": current_price - 58.0, "high": current_price - 27.8, "low": current_price - 61.0, "close": current_price - 43.5},
        ],
        atr_m1=1.1,
    )


def _build_test_db():
    db_dir = Path("F:/observerai-magnet-engine/.tmp-test-dbs")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"observerai-best-{uuid4().hex}.db"
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


def test_best_signal_returns_highest_confidence_tradeable_setup():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request("GBPJPY", 201.40), db=db)
            evaluate_oracle_post(_sample_oracle_request("BTCUSD", 64882.40), db=db)
            evaluate_oracle_post(_sample_oracle_request("XAUUSD", 3358.40), db=db)

            payload = best_signal(db=db).model_dump()
            ea_payload = ea_best_signal(db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert payload["tradeable"] is True
    assert payload["symbol"] in {"XAUUSD", "GBPJPY", "BTCUSD"}
    assert payload["action"] in {"BUY", "SELL"}
    assert payload["confidence"] is not None
    assert payload["target"] is not None
    assert payload["target_type"] == "atr"
    assert payload["reason"] == "Highest confidence active directional setup"
    assert ea_payload["tradeable"] is True
    assert ea_payload["symbol"] == payload["symbol"]


def test_best_signal_returns_clean_empty_state_when_no_tradeable_signal():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            payload = best_signal(db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert payload["tradeable"] is False
    assert payload["message"] == "No strong signal available"


def test_ea_routes_filter_out_low_confidence_setups():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        low_confidence = evaluate_oracle().model_copy(update={"confidence": 80})
        with testing_session_local() as db:
            save_evaluated_signal(db, low_confidence)
            best_payload = ea_best_signal(db=db).model_dump()
            latest_payload = ea_latest_signal(symbol="XAUUSD", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert best_payload["tradeable"] is False
    assert best_payload["message"] == "No strong signal available"
    assert latest_payload["symbol"] == "XAUUSD"
    assert latest_payload["tradeable"] is False
    assert latest_payload["message"] == "No strong signal available"
    assert latest_payload["action"] is None


def test_ea_routes_support_tp_modes():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request("XAUUSD", 3358.40), db=db)
            atr_payload = ea_latest_signal(symbol="XAUUSD", tp_mode="ATR", db=db).model_dump()
            magnet_payload = ea_latest_signal(symbol="XAUUSD", tp_mode="MAGNET", db=db).model_dump()
            rr_payload = ea_latest_signal(symbol="XAUUSD", tp_mode="RR", rr_multiple=2.0, db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert atr_payload["target_type"] == "atr"
    assert atr_payload["target"] == 3359.9
    assert magnet_payload["target_type"] == "magnet"
    assert magnet_payload["target"] == magnet_payload["dashboard_target"]
    assert magnet_payload["target"] > atr_payload["target"]
    assert rr_payload["target_type"] == "rr_2.0"
    assert rr_payload["target"] > magnet_payload["target"]


def test_ea_api_key_blocks_missing_header_when_configured(monkeypatch):
    monkeypatch.setenv("EA_API_KEY", "observer-ea-secret")
    get_settings.cache_clear()
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/ea/best-signal",
            "headers": [],
            "query_string": b"symbol=GBPJPY",
            "client": ("127.0.0.1", 1234),
        }
    )

    try:
        try:
            require_ea_api_key(request, x_ea_api_key=None)
            assert False, "Expected HTTPException for missing EA API key"
        except HTTPException as exc:
            assert exc.status_code == 403
    finally:
        monkeypatch.delenv("EA_API_KEY", raising=False)
        get_settings.cache_clear()
