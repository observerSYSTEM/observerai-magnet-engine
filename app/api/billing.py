import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.audit import audit_event, require_admin_access
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.billing import CreateCheckoutSessionRequest, CreateCheckoutSessionResponse
from app.services.billing_service import create_checkout_session_url

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post(
    "/create-checkout-session",
    response_model=CreateCheckoutSessionResponse,
    dependencies=[Depends(rate_limit("billing_checkout", limit=10, window_seconds=60))],
)
def create_checkout_session(
    payload: CreateCheckoutSessionRequest,
) -> CreateCheckoutSessionResponse:
    try:
        url = create_checkout_session_url(
            price_id=payload.price_id,
            settings=get_settings(),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return CreateCheckoutSessionResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    settings = get_settings()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured.",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from exc

    event_type = event["type"]

    # Minimal safe handling for now
    if event_type == "checkout.session.completed":
        pass
    elif event_type == "invoice.payment_succeeded":
        pass
    elif event_type == "customer.subscription.created":
        pass
    elif event_type == "customer.subscription.updated":
        pass
    elif event_type == "customer.subscription.deleted":
        pass

    return {"received": True}


@router.get(
    "/admin/config",
    dependencies=[
        Depends(rate_limit("billing_admin_config", limit=20, window_seconds=60)),
    ],
)
def billing_admin_config(
    request: Request,
    current_user: User = Depends(require_admin_access),
) -> dict[str, object]:
    settings = get_settings()
    audit_event(
        "billing_admin_config_view",
        actor=current_user.email,
        request=request,
        stripe_configured=bool(settings.stripe_secret_key),
    )
    return {
        "frontend_base_url": settings.frontend_base_url,
        "stripe_configured": bool(settings.stripe_secret_key),
    }