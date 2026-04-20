from __future__ import annotations

from app.schemas.signal import StoredSignalOut


def _format_magnet_name(signal: StoredSignalOut, magnet_name: str) -> str:
    magnet = getattr(signal, magnet_name)
    if magnet is None:
        return "none"
    return f"{magnet.name} {magnet.price:.2f}"


def build_alert_message(signal: StoredSignalOut) -> str:
    """Build a readable Telegram message from a stored oracle signal."""

    target = "none" if signal.intent.target is None else f"{signal.intent.target:.2f}"
    stop_hint = signal.intent.stop_hint or "none"

    return (
        f"{signal.symbol} | {signal.intent.action} {signal.intent.entry_type.upper()}\n\n"
        f"Bias: {signal.resolved_bias}\n"
        f"Event: {signal.event_type}\n"
        f"Price: {signal.current_price:.2f}\n"
        f"Target: {target}\n"
        f"Stop Hint: {stop_hint}\n"
        f"Nearest Magnet: {_format_magnet_name(signal, 'nearest_magnet')}\n"
        f"Major Magnet: {_format_magnet_name(signal, 'major_magnet')}\n"
        f"Confidence: {signal.confidence}\n"
        f"ADR Used: {signal.adr_used_pct:.2f}% ({signal.adr_state})"
    )
