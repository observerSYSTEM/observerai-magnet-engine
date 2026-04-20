from pydantic import BaseModel, ConfigDict, Field


class CreateCheckoutSessionRequest(BaseModel):
    """Request payload for creating a Stripe Checkout Session."""

    model_config = ConfigDict(extra="forbid")

    price_id: str = Field(min_length=1, max_length=128)


class CreateCheckoutSessionResponse(BaseModel):
    """Response containing the Stripe Checkout redirect URL."""

    url: str
