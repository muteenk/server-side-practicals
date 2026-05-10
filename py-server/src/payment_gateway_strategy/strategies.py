from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
import time

from fastapi import HTTPException, Request


@dataclass(frozen=True, slots=True)
class ChargeResult:
    gateway_name: str
    transaction_id: str
    amount_cents: int
    currency: str
    raw_metadata: dict


class PaymentGatewayStrategy(ABC):
    """Interchangeable implementation: each gateway encapsulates its own charge contract."""

    @abstractmethod
    def charge(self, amount_cents: int, currency: str, reference: str) -> ChargeResult:
        raise NotImplementedError


class StripeGateway(PaymentGatewayStrategy):
    def charge(self, amount_cents: int, currency: str, reference: str) -> ChargeResult:
        tx = f"ch_{secrets.token_hex(8)}"
        return ChargeResult(
            gateway_name="stripe",
            transaction_id=tx,
            amount_cents=amount_cents,
            currency=currency.upper(),
            raw_metadata={
                "object": "charge",
                "id": tx,
                "metadata": {"order_ref": reference},
                "captured": True,
            },
        )


class PayPalGateway(PaymentGatewayStrategy):
    def charge(self, amount_cents: int, currency: str, reference: str) -> ChargeResult:
        tx = secrets.token_hex(10).upper()
        return ChargeResult(
            gateway_name="paypal",
            transaction_id=tx,
            amount_cents=amount_cents,
            currency=currency.upper(),
            raw_metadata={
                "purchase_units": [
                    {
                        "reference_id": reference,
                        "amount": {
                            "currency_code": currency.upper(),
                            "value": f"{amount_cents / 100:.2f}",
                        },
                    }
                ],
                "status": "COMPLETED",
            },
        )


class RazorpayGateway(PaymentGatewayStrategy):
    def charge(self, amount_cents: int, currency: str, reference: str) -> ChargeResult:
        tx = f"pay_{int(time.time() * 1000)}_{secrets.token_hex(4)}"
        return ChargeResult(
            gateway_name="razorpay",
            transaction_id=tx,
            amount_cents=amount_cents,
            currency=currency.upper(),
            raw_metadata={
                "id": tx,
                "entity": "payment",
                "notes": {"order_id": reference},
                "status": "captured",
            },
        )


_GATEWAY_FACTORIES: dict[str, type[PaymentGatewayStrategy]] = {
    "stripe": StripeGateway,
    "paypal": PayPalGateway,
    "razorpay": RazorpayGateway,
}


def list_gateway_keys() -> list[str]:
    return sorted(_GATEWAY_FACTORIES.keys())


def create_gateway(name: str) -> PaymentGatewayStrategy:
    key = name.strip().lower()
    factory = _GATEWAY_FACTORIES.get(key)
    if not factory:
        allowed = ", ".join(list_gateway_keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown payment gateway {name!r}. Use one of: {allowed}",
        )
    return factory()


def resolve_gateway_from_request(request: Request) -> PaymentGatewayStrategy:
    """
    Pick implementation without the rest of the app branching on gateway names.
    Header wins over PAYMENT_GATEWAY env (default: stripe).
    """
    header = request.headers.get("x-payment-gateway")
    env_default = os.getenv("PAYMENT_GATEWAY", "stripe")
    name = (header or env_default).strip()
    return create_gateway(name)
