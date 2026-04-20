from __future__ import annotations

from typing import Any

from app.core.config import Settings


def _get_stripe_module() -> Any:
    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError(
            "Stripe package is required for billing. Install it from requirements.txt."
        ) from exc
    return stripe


def _extract_session_url(session: Any) -> str | None:
    if isinstance(session, dict):
        return session.get("url")
    return getattr(session, "url", None)


def create_checkout_session_url(
    *,
    price_id: str,
    settings: Settings,
    stripe_client: Any | None = None,
) -> str:
    """
    Create a Stripe Checkout Session in subscription mode and return its URL.
    """

    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

    frontend_base_url = settings.frontend_base_url.rstrip("/")
    stripe = stripe_client or _get_stripe_module()
    stripe.api_key = settings.stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{frontend_base_url}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend_base_url}/?checkout=cancelled",
    )
    url = _extract_session_url(session)
    if not url:
        raise RuntimeError("Stripe Checkout did not return a session URL.")
    return url
