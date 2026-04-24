from __future__ import annotations

from app.schemas.signal import SignalLifecycleOut

ACTIONABLE_ACTIONS = {"BUY", "SELL"}


def is_actionable_signal(action: str | None) -> bool:
    return (action or "").upper() in ACTIONABLE_ACTIONS


def derive_signal_lifecycle(
    *,
    action: str | None,
    outcome_status: str | None,
    closed_at,
) -> SignalLifecycleOut:
    """Resolve a dashboard-friendly lifecycle state from action and outcome data."""

    actionable = is_actionable_signal(action)
    normalized_status = (outcome_status or "").lower()

    if normalized_status == "target_hit":
        state = "Target Hit"
    elif normalized_status == "invalidated":
        state = "Invalidated"
    elif normalized_status == "expired":
        state = "Expired"
    elif actionable:
        state = "Setup Confirmed"
        normalized_status = "open"
    else:
        state = "Setup Forming"
        normalized_status = "not_tracking"

    return SignalLifecycleOut(
        state=state,
        outcome_status=normalized_status or "not_tracking",
        tracking_enabled=actionable,
        target_hit=normalized_status == "target_hit",
        invalidated=normalized_status == "invalidated",
        expired=normalized_status == "expired",
        closed_at=closed_at,
    )
