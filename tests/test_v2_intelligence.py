from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.oracle import evaluate_oracle_post
from app.api.stocks import weekly_stock_opportunities
from app.api.v2 import v2_dashboard_summary, v2_intelligence as v2_intelligence_route
from app.core.config import get_settings
from app.db.base import Base
from app.schemas.oracle import OracleEvaluateRequest
from app.schemas.v2 import Anchor0801BiasOut
from app.services.best_signal_service import is_tradeable_signal
from app.services.news_context import compute_news_context
from app.services.signal_service import list_latest_signals, save_evaluated_signal
from app.services.v2_intelligence import (
    compute_0801_bias,
    compute_discount_premium_zone,
    compute_h1_h4_liquidity_magnets,
    compute_m15_midlevel_break,
)


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
    db_path = db_dir / f"observerai-v2-{uuid4().hex}.db"
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


def test_0801_bias_returns_neutral_when_anchor_missing():
    payload = _sample_oracle_request().model_copy(
        update={
            "m1_candles": [
                candle
                for candle in _sample_oracle_request().m1_candles
                if candle.time.isoformat().replace("+00:00", "Z") != "2026-04-19T07:01:00Z"
            ]
        }
    )

    anchor = compute_0801_bias(payload)

    assert anchor.bias == "neutral"
    assert anchor.anchor_type == "neutral"
    assert "not found" in anchor.reason.lower()


def test_discount_premium_calculation():
    anchor = Anchor0801BiasOut(
        anchor_high=100.0,
        anchor_low=90.0,
        anchor_mid=95.0,
        anchor_type="body_acceptance",
        bias="bullish",
        reason="sample",
    )

    premium = compute_discount_premium_zone(anchor, 99.0)
    mid = compute_discount_premium_zone(anchor, 95.2)
    discount = compute_discount_premium_zone(anchor, 91.0)

    assert premium.price_position == "premium"
    assert mid.price_position == "mid"
    assert discount.price_position == "discount"


def test_m15_break_above_midlevel():
    payload = _sample_oracle_request().model_copy(
        update={
            "prev_m15_close": 99.5,
            "m15_candles": [
                {"time": "2026-04-19T10:00:00", "open": 99.0, "high": 99.7, "low": 98.8, "close": 99.4},
                {"time": "2026-04-19T10:15:00", "open": 99.4, "high": 101.4, "low": 99.2, "close": 100.8},
            ],
        }
    )
    anchor = Anchor0801BiasOut(
        anchor_high=101.0,
        anchor_low=99.0,
        anchor_mid=100.0,
        anchor_type="body_acceptance",
        bias="bullish",
        reason="sample",
    )

    result = compute_m15_midlevel_break(payload, anchor, next_level=101.4)

    assert result.confirmed is True
    assert result.direction == "break_up"
    assert result.next_level == 101.4


def test_wait_signal_is_not_tradeable():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        wait_payload = _sample_oracle_request()
        with testing_session_local() as db:
            base_response = evaluate_oracle_post(wait_payload, db=db)
            response = base_response.model_copy(
                update={
                    "intent": base_response.intent.model_copy(
                        update={
                            "action": "WAIT",
                            "entry_type": "none",
                            "reason": "Waiting for clearer alignment.",
                            "target": None,
                            "stop_hint": None,
                        }
                    )
                }
            )
            save_evaluated_signal(db, response)
            latest = list_latest_signals(db, "XAUUSD", limit=1).items[0]
    finally:
        _cleanup_test_db(db_path, engine)

    assert latest.intent.action == "WAIT"
    assert is_tradeable_signal(latest) is False


def test_h1_h4_magnets_return_clean_empty_state():
    payload = _sample_oracle_request().model_copy(update={"h1_candles": None, "h4_candles": None})

    liquidity = compute_h1_h4_liquidity_magnets(payload)

    assert liquidity.strongest_magnet is None
    assert liquidity.h1_magnets == []
    assert liquidity.h4_magnets == []


def test_v2_routes_return_stored_snapshot_and_symbol_summary():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            intelligence = v2_intelligence_route(symbol="XAUUSD", db=db).model_dump()
            summary = v2_dashboard_summary(db=db).model_dump()
    finally:
        _cleanup_test_db(db_path, engine)

    assert intelligence["symbol"] == "XAUUSD"
    assert "anchor_0801" in intelligence
    assert "highest_probability_direction" in intelligence
    assert summary["symbols"]
    assert any(item["symbol"] == "XAUUSD" for item in summary["symbols"])


def test_stock_opportunities_endpoint_returns_list():
    payload = weekly_stock_opportunities().model_dump()

    assert "opportunities" in payload
    assert isinstance(payload["opportunities"], list)


def test_news_context_returns_safe_neutral_state_if_api_key_missing(monkeypatch):
    monkeypatch.setenv("NEWS_API_PROVIDER", "finnhub")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    get_settings.cache_clear()

    try:
        payload = compute_news_context("XAUUSD").model_dump()
    finally:
        monkeypatch.delenv("NEWS_API_PROVIDER", raising=False)
        get_settings.cache_clear()

    assert payload["has_high_impact_news"] is False
    assert payload["expected_direction"] == "neutral"
    assert payload["trade_policy"] == "normal"
