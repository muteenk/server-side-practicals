"""
Deliberately ugly: every gateway is another branch in one function.

Use this in the tutorial as the “before” — new provider = edit this pile of elifs,
merge conflicts, and easy-to-miss copy-paste bugs. The Strategy version moves each
branch into its own class and keeps the HTTP layer dumb.
"""

import os
import secrets
import time

from fastapi import HTTPException, Request

from .pydantic_models import ChargeRequest, ChargeResponse


def charge_with_hardcoded_gateways(request: Request, payload: ChargeRequest) -> ChargeResponse:
    header = request.headers.get("x-payment-gateway")
    env_default = os.getenv("PAYMENT_GATEWAY", "stripe")
    gateway = (header or env_default).strip().lower()

    currency = payload.currency.upper()
    ref = payload.reference
    amount = payload.amount_cents

    if gateway == "stripe":
        tx = f"ch_{secrets.token_hex(8)}"
        return ChargeResponse(
            gateway="stripe",
            transaction_id=tx,
            amount_cents=amount,
            currency=currency,
            gateway_metadata={
                "object": "charge",
                "id": tx,
                "metadata": {"order_ref": ref},
                "captured": True,
            },
        )

    elif gateway == "paypal":
        tx = secrets.token_hex(10).upper()
        return ChargeResponse(
            gateway="paypal",
            transaction_id=tx,
            amount_cents=amount,
            currency=currency,
            gateway_metadata={
                "purchase_units": [
                    {
                        "reference_id": ref,
                        "amount": {
                            "currency_code": currency,
                            "value": f"{amount / 100:.2f}",
                        },
                    }
                ],
                "status": "COMPLETED",
            },
        )

    elif gateway == "razorpay":
        tx = f"pay_{int(time.time() * 1000)}_{secrets.token_hex(4)}"
        return ChargeResponse(
            gateway="razorpay",
            transaction_id=tx,
            amount_cents=amount,
            currency=currency,
            gateway_metadata={
                "id": tx,
                "entity": "payment",
                "notes": {"order_id": ref},
                "status": "captured",
            },
        )
    elif gateway == "juspay":
        pass
    elif gateway == "paytm":
        pass

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown gateway {gateway!r}. "
                "You must open this file and add another elif (and hope you did not break PayPal)."
            ),
        )
