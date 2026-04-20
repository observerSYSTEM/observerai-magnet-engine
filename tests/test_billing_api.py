from types import SimpleNamespace
from unittest.mock import patch

from app.api.billing import create_checkout_session
from app.core.config import Settings
from app.schemas.billing import CreateCheckoutSessionRequest
from app.services.billing_service import create_checkout_session_url


class _FakeStripeSessionApi:
    last_kwargs: dict | None = None

    @classmethod
    def create(cls, **kwargs):
        cls.last_kwargs = kwargs
        return {"url": "https://checkout.stripe.test/session_123"}


class _FakeStripe:
    api_key = ""
    checkout = SimpleNamespace(Session=_FakeStripeSessionApi)


def test_create_checkout_session_url_uses_subscription_mode():
    settings = Settings(
        STRIPE_SECRET_KEY="sk_test_123",
        FRONTEND_BASE_URL="http://127.0.0.1:8000",
    )

    url = create_checkout_session_url(
        price_id="price_123",
        settings=settings,
        stripe_client=_FakeStripe,
    )

    assert url == "https://checkout.stripe.test/session_123"
    assert _FakeStripe.api_key == "sk_test_123"
    assert _FakeStripeSessionApi.last_kwargs["mode"] == "subscription"
    assert _FakeStripeSessionApi.last_kwargs["line_items"] == [{"price": "price_123", "quantity": 1}]
    assert _FakeStripeSessionApi.last_kwargs["success_url"].startswith("http://127.0.0.1:8000/")
    assert _FakeStripeSessionApi.last_kwargs["cancel_url"] == "http://127.0.0.1:8000/?checkout=cancelled"


def test_create_checkout_session_route_returns_url():
    payload = CreateCheckoutSessionRequest(price_id="price_123")
    settings = Settings(
        STRIPE_SECRET_KEY="sk_test_123",
        FRONTEND_BASE_URL="http://127.0.0.1:8000",
    )

    with patch("app.api.billing.get_settings", return_value=settings):
        with patch(
            "app.api.billing.create_checkout_session_url",
            return_value="https://checkout.stripe.test/session_456",
        ):
            response = create_checkout_session(payload)

    assert response.url == "https://checkout.stripe.test/session_456"
