"""
Smallest possible integration: one provider, wired directly.

Fine for an MVP, but the moment you need PayPal, region-specific rails, or failover,
you start bolting on conditionals (see `hardcoded_checkout.py`) or you refactor to
Strategy (`strategies.py` + `CheckoutService`).
"""

import secrets

from .pydantic_models import ChargeRequest, ChargeResponse


def charge_paypal_only(payload: ChargeRequest) -> ChargeResponse:
    """No switching: Paypla is the only supported gateway, always."""
    currency = payload.currency.upper()
    tx = f"ch_{secrets.token_hex(8)}"
    return ChargeResponse(
        gateway="paypal",
        transaction_id=tx,
        amount_cents=payload.amount_cents,
        extra="extra",
        currency=currency,
        gateway_metadata={
            "object": "charge",
            "id": tx,
            "param": {},
            "metadata": {"order_ref": payload.reference},
            "captured": True,
        },
    )
