from pydantic import BaseModel, Field


class ChargeRequest(BaseModel):
    amount_cents: int = Field(..., gt=0, description="Amount in smallest currency unit (e.g. cents)")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    reference: str = Field(
        default="demo-order",
        description="Merchant reference / order id forwarded to the gateway",
    )


class ChargeResponse(BaseModel):
    gateway: str
    transaction_id: str
    amount_cents: int
    currency: str
    gateway_metadata: dict


class GatewayInfo(BaseModel):
    key: str
    display_name: str
    summary: str
