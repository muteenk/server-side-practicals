from .strategies import ChargeResult, PaymentGatewayStrategy


class CheckoutService:
    """
    Context object: orchestration stays stable; only the injected strategy changes.
    """

    def __init__(self, gateway: PaymentGatewayStrategy) -> None:
        self._gateway = gateway

    def charge(self, amount_cents: int, currency: str, reference: str) -> ChargeResult:
        return self._gateway.charge(amount_cents, currency, reference)
