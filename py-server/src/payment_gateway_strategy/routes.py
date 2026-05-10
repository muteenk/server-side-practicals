from fastapi import APIRouter, Request

from src import dependencies

from .hardcoded_checkout import charge_with_hardcoded_gateways
from .pydantic_models import ChargeRequest, ChargeResponse, GatewayInfo
from .single_gateway_checkout import charge_paypal_only


router = APIRouter(prefix="/strategy-pattern/payment", tags=["strategy_pattern_payment"])

legacy_hardcoded_router = APIRouter(
    prefix="/strategy-pattern/payment-hardcoded",
    tags=["strategy_pattern_payment_hardcoded"],
)

single_gateway_router = APIRouter(
    prefix="/strategy-pattern/payment-single-gateway",
    tags=["strategy_pattern_payment_single_gateway"],
)


@router.get("/gateways", response_model=list[GatewayInfo])
def list_gateways() -> list[GatewayInfo]:
    return [
        GatewayInfo(
            key="stripe",
            display_name="Stripe",
            summary="Card-style charge object; swap via X-Payment-Gateway: stripe",
        ),
        GatewayInfo(
            key="paypal",
            display_name="PayPal",
            summary="Purchase-units shaped payload; same endpoint, different strategy",
        ),
        GatewayInfo(
            key="razorpay",
            display_name="Razorpay",
            summary="India-common gateway shape; still one checkout code path",
        ),
    ]


@router.post("/charge", response_model=ChargeResponse)
def charge(
    payload: ChargeRequest,
    checkout: dependencies.CheckoutServiceDep,
) -> ChargeResponse:
    """
    Same handler for every gateway: the strategy is selected by dependency injection
    (header `X-Payment-Gateway` or env `PAYMENT_GATEWAY`).
    """
    result = checkout.charge(
        payload.amount_cents,
        payload.currency,
        payload.reference,
    )
    return ChargeResponse(
        gateway=result.gateway_name,
        transaction_id=result.transaction_id,
        amount_cents=result.amount_cents,
        currency=result.currency,
        gateway_metadata=result.raw_metadata,
    )


@legacy_hardcoded_router.post("/charge", response_model=ChargeResponse)
def charge_hardcoded_branching(
    request: Request,
    payload: ChargeRequest,
) -> ChargeResponse:
    """
    Same inputs as `/strategy-pattern/payment/charge`, but the route calls one function
    full of `if gateway == ...` branches — see `hardcoded_checkout.py`.
    """
    return charge_with_hardcoded_gateways(request, payload)


@single_gateway_router.post("/charge", response_model=ChargeResponse)
def charge_single_hardcoded_provider(payload: ChargeRequest) -> ChargeResponse:
    """
    Only Stripe exists in this codebase path — no header, no env, no abstraction.
    See `single_gateway_checkout.py`.
    """
    return charge_paypal_only(payload)
