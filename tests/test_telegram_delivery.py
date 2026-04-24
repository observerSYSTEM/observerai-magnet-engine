from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.oracle import evaluate_oracle, evaluate_oracle_post
from app.db.base import Base
from app.schemas.oracle import IntentOut, MagnetInfo, OracleEvaluateRequest
from app.services.performance_service import evaluate_open_signal_outcomes
from app.services.signal_service import save_evaluated_signal
from app.services.telegram_service import deliver_signal_alert, deliver_signal_outcome_alerts


def _build_test_db():
    db_dir = Path("F:/observerai-magnet-engine/.tmp-test-dbs")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"observerai-telegram-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    testing_session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return db_path, engine, testing_session_local


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


def _sender_collector(messages: list[str]):
    def _sender(message: str) -> bool:
        messages.append(message)
        return True

    return _sender


def test_dedupe_blocks_repeated_identical_actionable_alert():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        baseline = evaluate_oracle()
        messages: list[str] = []

        with testing_session_local() as db:
            first_row = save_evaluated_signal(db, baseline)
            assert deliver_signal_alert(db, first_row, sender=_sender_collector(messages)) is True

            second_row = save_evaluated_signal(db, baseline)
            assert deliver_signal_alert(db, second_row, sender=_sender_collector(messages)) is False
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert len(messages) == 1
    assert "ObserverAI Signal Alert" in messages[0]
    assert "Status: Setup Confirmed" in messages[0]
    assert "Action: Buy Signal" in messages[0]
    assert "Bias: Bullish Continuation" in messages[0]
    assert "bullish_continuation" not in messages[0]


def test_new_alert_allowed_when_target_changes():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        baseline = evaluate_oracle()
        updated = baseline.model_copy(
            update={
                "nearest_magnet": MagnetInfo(
                    name="ADR_HIGH",
                    price=3372.8,
                    direction="bullish",
                    strength=8.0,
                    source="adr",
                ),
                "major_magnet": MagnetInfo(
                    name="ADR_HIGH",
                    price=3372.8,
                    direction="bullish",
                    strength=8.0,
                    source="adr",
                ),
                "intent": IntentOut(
                    action=baseline.intent.action,
                    entry_type=baseline.intent.entry_type,
                    reason=baseline.intent.reason,
                    target=3372.8,
                    stop_hint=baseline.intent.stop_hint,
                ),
                "message": baseline.message.replace("3361.40000", "3372.80000"),
            }
        )
        messages: list[str] = []

        with testing_session_local() as db:
            save_evaluated_signal(db, baseline)
            changed_row = save_evaluated_signal(db, updated)

            assert deliver_signal_alert(db, changed_row, sender=_sender_collector(messages)) is True
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert len(messages) == 1
    assert "Target: 3372.80" in messages[0]
    assert "Nearest Magnet: ADR High 3372.80" in messages[0]


def test_non_actionable_wait_signal_does_not_send():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        baseline = evaluate_oracle()
        standby = baseline.model_copy(
            update={
                "resolved_bias": "neutral_wait",
                "intent": IntentOut(
                    action="WAIT",
                    entry_type="none",
                    reason="No clear alignment yet.",
                    target=None,
                    stop_hint=None,
                ),
            }
        )
        messages: list[str] = []

        with testing_session_local() as db:
            wait_row = save_evaluated_signal(db, standby)
            assert deliver_signal_alert(db, wait_row, sender=_sender_collector(messages)) is False
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert messages == []


def test_target_hit_lifecycle_alert_is_sent_when_outcome_changes():
    db_path, engine, testing_session_local = _build_test_db()
    try:
        messages: list[str] = []

        with testing_session_local() as db:
            evaluate_oracle_post(_sample_oracle_request(), db=db)
            changed = evaluate_open_signal_outcomes(
                db,
                symbol="XAUUSD",
                current_price=3361.40,
            )
            delivered = deliver_signal_outcome_alerts(db, changed, sender=_sender_collector(messages))
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert delivered == 1
    assert len(messages) == 1
    assert "Status: Target Hit" in messages[0]
    assert "Action: Buy Signal" in messages[0]
    assert "Target reached and the signal closed successfully." in messages[0]
