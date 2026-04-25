from __future__ import annotations

import re

from app.schemas.signal import StoredSignalOut

SYMBOL_ICONS = {
    "XAUUSD": "🟡",
    "GBPJPY": "🔵",
    "BTCUSD": "🟠",
}

LABEL_OVERRIDES = {
    "bullish_continuation": "Bullish Continuation",
    "bearish_continuation": "Bearish Continuation",
    "bullish_reversal": "Bullish Reversal",
    "bearish_reversal": "Bearish Reversal",
    "neutral_outside_value": "Neutral Outside Value",
    "neutral_wait": "Neutral Wait",
    "equal_highs": "Equal Highs",
    "equal_lows": "Equal Lows",
    "adr_high": "ADR High",
    "adr_low": "ADR Low",
    "no_event": "No Event",
    "no_mid_flow": "No Mid Flow",
    "mid_compression": "Mid Compression",
    "bullish_mid_to_mid": "Bullish Mid-to-Mid",
    "bearish_mid_to_mid": "Bearish Mid-to-Mid",
    "none": "None",
}

TOKEN_OVERRIDES = {
    "adr": "ADR",
    "bos": "BOS",
    "btcusd": "BTCUSD",
    "eq": "EQ",
    "gbpjpy": "GBPJPY",
    "m1": "M1",
    "m15": "M15",
    "mss": "MSS",
    "mt5": "MT5",
    "pdh": "PDH",
    "pdl": "PDL",
    "xauusd": "XAUUSD",
}

REASON_TEMPLATES = {
    "bullish_continuation": "Bullish continuation confirmed",
    "bearish_continuation": "Bearish continuation confirmed",
    "bullish_reversal": "Bullish reversal confirmed",
    "bearish_reversal": "Bearish reversal confirmed",
    "neutral_outside_value": "Price is outside value without strong alignment",
    "neutral_wait": "No clear directional alignment yet",
}


def _humanize_label(value: str | None) -> str:
    if not value:
        return "None"

    normalized = value.strip()
    if not normalized:
        return "None"

    lowered = normalized.lower()
    if lowered in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[lowered]

    parts = re.split(r"[_\s]+", normalized)
    words = []
    for part in parts:
        if not part:
            continue
        token = TOKEN_OVERRIDES.get(part.lower())
        words.append(token if token is not None else part.title())
    return " ".join(words) or "None"


def _format_symbol(symbol: str) -> str:
    upper_symbol = symbol.upper()
    icon = SYMBOL_ICONS.get(upper_symbol)
    return f"{icon} {upper_symbol}" if icon else upper_symbol


def _format_price(value: float | None, *, default: str = "None") -> str:
    if value is None:
        return default
    return f"{value:.2f}"


def _format_action(action: str) -> str:
    normalized = action.upper()
    if normalized == "BUY":
        return "Buy Signal"
    if normalized == "SELL":
        return "Sell Signal"
    return "Standby"


def _format_status(signal: StoredSignalOut) -> str:
    if signal.lifecycle and signal.lifecycle.state:
        return signal.lifecycle.state
    if signal.intent.action in {"BUY", "SELL"}:
        return "Setup Confirmed"
    return "Setup Forming"


def _format_magnet_name(magnet) -> str:
    if magnet is None:
        return "None"
    return f"{_humanize_label(magnet.name)} {magnet.price:.2f}"


def _format_stop_hint(signal: StoredSignalOut) -> str:
    if not signal.intent.stop_hint:
        return "None"
    return _humanize_label(signal.intent.stop_hint)


def _format_momentum(signal: StoredSignalOut) -> str:
    if signal.momentum is None:
        return "Neutral"
    return (
        f"{_humanize_label(signal.momentum.direction)} / "
        f"{_humanize_label(signal.momentum.classification)}"
    )


def _format_structure(signal: StoredSignalOut) -> str:
    if signal.structure is None:
        return "Neutral"
    if signal.structure.type == "none" or signal.structure.direction == "neutral":
        return "Neutral"
    return (
        f"{_humanize_label(signal.structure.type)} / "
        f"{_humanize_label(signal.structure.direction)}"
    )


def _strength_label(strength: float) -> str:
    if strength >= 0.67:
        return "Strong"
    if strength >= 0.34:
        return "Moderate"
    return "Weak"


def _format_sweep(signal: StoredSignalOut) -> str:
    if signal.sweep is None or signal.sweep.type == "none":
        return "None"
    return f"{_humanize_label(signal.sweep.type)} / {_strength_label(signal.sweep.strength)}"


def _normalize_reason_text(reason: str) -> str:
    cleaned = " ".join(reason.replace("_", " ").split()).strip(" .")
    if not cleaned:
        return ""
    return cleaned[:1].upper() + cleaned[1:]


def _truncate_reason(reason: str, max_length: int = 88) -> str:
    if len(reason) <= max_length:
        return reason if reason.endswith(".") else f"{reason}."

    truncated = reason[: max_length - 3].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}..."


def _build_reason(signal: StoredSignalOut) -> str:
    lifecycle_state = _format_status(signal)
    if lifecycle_state == "Target Hit":
        return "Target reached and the signal closed successfully."
    if lifecycle_state == "Invalidated":
        return "Invalidation level was breached and the setup was closed."
    if lifecycle_state == "Expired":
        return "Tracking window expired before a target or invalidation was reached."

    template = REASON_TEMPLATES.get(signal.resolved_bias)
    if template is not None:
        if signal.resolved_bias.startswith("bullish"):
            return f"{template} with upside magnet alignment."
        if signal.resolved_bias.startswith("bearish"):
            return f"{template} with downside magnet alignment."
        return f"{template}."

    if signal.intent.reason:
        return _truncate_reason(_normalize_reason_text(signal.intent.reason))

    return "Structured signal context detected."


def build_alert_message(signal: StoredSignalOut) -> str:
    """Build a polished Telegram message from a stored oracle signal."""

    lifecycle_status = _format_status(signal)
    status_line = ""
    if lifecycle_status not in {"Setup Confirmed", "Setup Forming"}:
        status_line = f"Status: {lifecycle_status}\n"

    htf_target = signal.liquidity_target or signal.telegram_target or signal.dashboard_target

    return (
        "⚡ ObserverAI Signal\n\n"
        f"Symbol: {_format_symbol(signal.symbol)}\n"
        f"{status_line}"
        f"Bias: {_humanize_label(signal.resolved_bias)}\n"
        f"Action: {_format_action(signal.intent.action)}\n"
        f"Confidence: {signal.confidence}%\n\n"
        "Execution Area:\n"
        f"Price: {_format_price(signal.current_price)}\n"
        f"Stop Hint: {_format_stop_hint(signal)}\n\n"
        "Liquidity Targets:\n"
        f"T1: {_format_magnet_name(signal.nearest_magnet)}\n"
        f"T2: {_format_magnet_name(signal.major_magnet)}\n"
        f"HTF Target: {_format_price(htf_target)}\n\n"
        "Market Structure:\n"
        f"Momentum: {_format_momentum(signal)}\n"
        f"Structure: {_format_structure(signal)}\n"
        f"Sweep: {_format_sweep(signal)}\n"
        f"ADR State: {_humanize_label(signal.adr_state)}\n\n"
        "Reason:\n"
        f"{_build_reason(signal)}\n\n"
        "EA Note:\n"
        "EA may use separate TP based on ATR/RR execution logic.\n\n"
        "ObserverAI Magnet Engine\n"
        "Structured signals. Measurable outcomes."
    )
