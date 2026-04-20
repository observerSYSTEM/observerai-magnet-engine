from __future__ import annotations

from datetime import timedelta

from app.schemas.signal import StoredSignalOut


ALERT_COOLDOWN_WINDOW = timedelta(minutes=5)
CONFIDENCE_CHANGE_THRESHOLD = 5


def signal_target(signal: StoredSignalOut) -> float | None:
    return signal.intent.target


def signal_key(symbol: str, resolved_bias: str, event_type: str, target: float | None) -> str:
    target_part = "none" if target is None else f"{target:.5f}"
    return f"{symbol}:{resolved_bias}:{event_type}:{target_part}"


def should_send_signal_alert(
    current_signal: StoredSignalOut,
    previous_signal: StoredSignalOut | None,
    cooldown_window: timedelta = ALERT_COOLDOWN_WINDOW,
    confidence_change_threshold: int = CONFIDENCE_CHANGE_THRESHOLD,
) -> bool:
    """
    Decide whether a Telegram alert should be sent for the current stored signal.

    Repeated alerts are suppressed when the symbol, resolved bias, event type, and
    target are unchanged within the cooldown window, unless confidence shifts by a
    meaningful amount.
    """

    if previous_signal is None:
        return True

    current_key = signal_key(
        current_signal.symbol,
        current_signal.resolved_bias,
        current_signal.event_type,
        signal_target(current_signal),
    )
    previous_key = signal_key(
        previous_signal.symbol,
        previous_signal.resolved_bias,
        previous_signal.event_type,
        signal_target(previous_signal),
    )

    if current_key != previous_key:
        return True

    if abs(current_signal.confidence - previous_signal.confidence) >= confidence_change_threshold:
        return True

    return (current_signal.created_at - previous_signal.created_at) > cooldown_window
