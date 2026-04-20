from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.oracle import evaluate_oracle
from app.db.base import Base
from app.schemas.oracle import IntentOut, MagnetInfo
from app.services.signal_service import save_evaluated_signal
from app.services.telegram_service import deliver_signal_alert


def _build_test_db():
    db_dir = Path("F:/observerai-magnet-engine/.tmp-test-dbs")
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / f"observerai-telegram-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return db_path, engine, TestingSessionLocal


def _sender_collector(messages: list[str]):
    def _sender(message: str) -> bool:
        messages.append(message)
        return True

    return _sender


def test_dedupe_blocks_repeated_identical_alert():
    db_path, engine, TestingSessionLocal = _build_test_db()
    try:
        baseline = evaluate_oracle()
        messages: list[str] = []

        with TestingSessionLocal() as db:
            first_row = save_evaluated_signal(db, baseline)
            assert deliver_signal_alert(db, first_row, sender=_sender_collector(messages)) is True

            second_row = save_evaluated_signal(db, baseline)
            assert deliver_signal_alert(db, second_row, sender=_sender_collector(messages)) is False
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert len(messages) == 1
    assert "BUY CONTINUATION" in messages[0]


def test_new_alert_allowed_when_target_changes():
    db_path, engine, TestingSessionLocal = _build_test_db()
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

        with TestingSessionLocal() as db:
            save_evaluated_signal(db, baseline)
            changed_row = save_evaluated_signal(db, updated)

            assert deliver_signal_alert(db, changed_row, sender=_sender_collector(messages)) is True
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert len(messages) == 1
    assert "3372.80" in messages[0]


def test_new_alert_allowed_when_confidence_changes_meaningfully():
    db_path, engine, TestingSessionLocal = _build_test_db()
    try:
        baseline = evaluate_oracle()
        updated = baseline.model_copy(
            update={
                "confidence": baseline.confidence + 6,
                "message": baseline.message + " | confidence-shift",
            }
        )
        messages: list[str] = []

        with TestingSessionLocal() as db:
            save_evaluated_signal(db, baseline)
            changed_row = save_evaluated_signal(db, updated)

            assert deliver_signal_alert(db, changed_row, sender=_sender_collector(messages)) is True
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)

    assert len(messages) == 1
