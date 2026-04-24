from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.signal import Signal
from app.models.signal_outcome import SignalOutcome
from app.services.alert_engine import build_alert_message
from app.services.lifecycle_service import is_actionable_signal
from app.services.signal_service import get_previous_signal_candidate, signal_row_to_stored_signal
from app.utils.dedupe import should_send_signal_alert

logger = logging.getLogger(__name__)


def send_telegram(message: str) -> bool:
    """Send a Telegram message using the configured bot and chat target."""

    settings = get_settings()
    if not settings.telegram_alerts_enabled:
        logger.info("Telegram alerts disabled; skipping send.")
        return False
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured; skipping send.")
        return False

    import httpx

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    with httpx.Client(timeout=10) as client:
        response = client.post(
            url,
            json={"chat_id": settings.telegram_chat_id, "text": message},
        )
        response.raise_for_status()
    return True


def deliver_signal_alert(
    db: Session,
    saved_signal: Signal,
    sender: Callable[[str], bool] | None = None,
) -> bool:
    """
    Deliver a Telegram alert for a saved signal when dedupe allows it.

    The comparison is based on the most recent prior stored signal in the same alert
    family. Telegram failures are logged and do not interrupt the evaluation flow.
    """

    current_signal = signal_row_to_stored_signal(saved_signal)
    if not is_actionable_signal(current_signal.intent.action):
        logger.info(
            "Skipping Telegram alert for non-actionable %s signal on %s.",
            current_signal.intent.action,
            current_signal.symbol,
        )
        return False

    previous_signal = get_previous_signal_candidate(db, saved_signal)

    if not should_send_signal_alert(current_signal, previous_signal):
        logger.info(
            "Skipping duplicate Telegram alert for %s %s %s.",
            current_signal.symbol,
            current_signal.resolved_bias,
            current_signal.event_type,
        )
        return False

    message = build_alert_message(current_signal)
    send_fn = sender or send_telegram

    try:
        return send_fn(message)
    except Exception:
        logger.exception(
            "Telegram delivery failed for %s %s.",
            current_signal.symbol,
            current_signal.event_type,
        )
        return False


def deliver_signal_outcome_alerts(
    db: Session,
    outcomes: list[SignalOutcome],
    sender: Callable[[str], bool] | None = None,
) -> int:
    """Deliver lifecycle alerts when tracked outcomes close materially."""

    send_fn = sender or send_telegram
    delivered = 0

    for outcome in outcomes:
        if outcome.outcome_status not in {"target_hit", "invalidated"}:
            continue

        signal = db.scalar(
            select(Signal)
            .options(selectinload(Signal.outcome))
            .where(Signal.id == outcome.signal_id)
        )
        if signal is None:
            continue

        try:
            if send_fn(build_alert_message(signal_row_to_stored_signal(signal))):
                delivered += 1
        except Exception:
            logger.exception(
                "Telegram lifecycle delivery failed for signal_id=%s status=%s.",
                outcome.signal_id,
                outcome.outcome_status,
            )
    return delivered
