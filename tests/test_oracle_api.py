from pathlib import Path
from fastapi.responses import HTMLResponse
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.ea import ea_latest_signal
from app.api.oracle import evaluate_oracle, evaluate_oracle_post
from app.api.signals import latest_signals
from app.db.base import Base
from app.main import root
from app.schemas.oracle import OracleEvaluateRequest


def _sample_oracle_request() -> OracleEvaluateRequest:
    return OracleEvaluateRequest(
        symbol="XAUUSD",
        current_price=3358.40,
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
            {"time": "2026-04-19T11:30:00", "open": 3356.3, "high": 3359.1, "low": 3355.8, "close": 3358.4},
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
    db_path = db_dir / f"observerai-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return db_path, engine, TestingSessionLocal


def _cleanup_test_db(db_path: Path, engine) -> None:
    engine.dispose()
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


def test_root():
    payload = root()

    assert isinstance(payload, HTMLResponse)
    body = payload.body.decode("utf-8")
    assert "ObserverAI Magnet Engine" in body
    assert "Start with Pro" in body
    assert "/billing/create-checkout-session" in body


def test_oracle_get_demo_includes_intent_contract():
    payload = evaluate_oracle().model_dump()

    assert payload["bias"]
    assert payload["resolved_bias"] == "bullish_continuation"
    assert payload["structure"]["type"] == "bos"
    assert payload["structure"]["direction"] == "bullish"
    assert payload["momentum"]["classification"] in {"moderate", "strong"}
    assert isinstance(payload["magnet_path"], list)
    assert payload["magnet_path"]
    assert payload["mid_targets"]["flow"] in {
        "bullish_mid_to_mid",
        "bearish_mid_to_mid",
        "mid_compression",
        "no_mid_flow",
    }
    assert payload["intent"]["action"] == "BUY"
    assert payload["intent"]["entry_type"] == "continuation"
    assert payload["intent"]["target"] == 3361.4


def test_oracle_post_evaluate_returns_expected_shape():
    db_path, engine, TestingSessionLocal = _build_test_db()
    try:
        with TestingSessionLocal() as db:
            payload = evaluate_oracle_post(_sample_oracle_request(), db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert payload["symbol"] == "XAUUSD"
    assert payload["event_type"] == "m15_close_above_anchor_value_high"
    assert payload["resolved_bias"] == "bullish_continuation"
    assert payload["nearest_magnet"]["price"] == 3361.4
    assert payload["major_magnet"]["price"] == 3361.4
    assert payload["magnet_path"][0]["price"] == 3361.4
    assert payload["structure"]["type"] == "bos"
    assert payload["structure"]["direction"] == "bullish"
    assert payload["sweep"]["type"] == "none"
    assert payload["momentum"]["direction"] == "bullish"
    assert payload["mid_targets"]["flow"] == "no_mid_flow"
    assert payload["confidence"] >= 0
    assert payload["intent"]["action"] == "BUY"
    assert payload["intent"]["entry_type"] == "continuation"
    assert payload["intent"]["target"] == 3361.4
    assert "mid_flow=no_mid_flow" in payload["message"]
    assert "action=BUY" in payload["message"]


def test_oracle_post_stores_signal_and_latest_returns_it():
    db_path, engine, TestingSessionLocal = _build_test_db()
    try:
        with TestingSessionLocal() as db:
            stored = evaluate_oracle_post(_sample_oracle_request(), db=db).model_dump()
            latest = latest_signals(symbol="XAUUSD", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert latest["count"] == 1
    assert latest["items"][0]["symbol"] == stored["symbol"]
    assert latest["items"][0]["current_price"] == stored["current_price"]
    assert latest["items"][0]["resolved_bias"] == stored["resolved_bias"]
    assert latest["items"][0]["event_type"] == stored["event_type"]
    assert latest["items"][0]["nearest_magnet"] == stored["nearest_magnet"]
    assert latest["items"][0]["major_magnet"] == stored["major_magnet"]
    assert latest["items"][0]["magnet_path"] == stored["magnet_path"]
    assert latest["items"][0]["sweep"] == stored["sweep"]
    assert latest["items"][0]["structure"] == stored["structure"]
    assert latest["items"][0]["momentum"] == stored["momentum"]
    assert latest["items"][0]["mid_targets"] == stored["mid_targets"]
    assert latest["items"][0]["intent"] == stored["intent"]
    assert latest["items"][0]["lifecycle"]["state"] == "Setup Confirmed"
    assert latest["items"][0]["lifecycle"]["outcome_status"] == "open"
    assert latest["items"][0]["lifecycle"]["target_hit"] is False
    assert latest["items"][0]["lifecycle"]["invalidated"] is False
    assert latest["items"][0]["confidence"] == stored["confidence"]


def test_oracle_post_stores_requested_symbol_and_ea_route_returns_it():
    db_path, engine, TestingSessionLocal = _build_test_db()
    try:
        gbpjpy_request = _sample_oracle_request().model_copy(update={"symbol": "GBPJPY"})
        with TestingSessionLocal() as db:
            stored = evaluate_oracle_post(gbpjpy_request, db=db).model_dump()
            gbpjpy_latest = latest_signals(symbol="GBPJPY", db=db).model_dump()
            xau_latest = latest_signals(symbol="XAUUSD", db=db).model_dump()
            ea_payload = ea_latest_signal(symbol="GBPJPY", db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert stored["symbol"] == "GBPJPY"
    assert gbpjpy_latest["symbol"] == "GBPJPY"
    assert gbpjpy_latest["count"] == 1
    assert gbpjpy_latest["items"][0]["symbol"] == "GBPJPY"
    assert xau_latest["symbol"] == "XAUUSD"
    assert xau_latest["count"] == 0
    assert ea_payload["symbol"] == "GBPJPY"
    assert ea_payload["action"] in {"BUY", "SELL"}
    assert ea_payload["bias"] in {"bullish_continuation", "bearish_continuation", "bullish_reversal", "bearish_reversal"}
    assert ea_payload["tradeable"] is True
    assert ea_payload["lifecycle"] == "setup_confirmed"
    assert ea_payload["nearest_magnet"] is not None
    assert ea_payload["major_magnet"] is not None
