from typing import Annotated

from fastapi import Depends, Request

from .idempotence import (
    services as idempotence_services,
    repository as idempotence_repo,
)
from .payment_gateway_strategy.services import CheckoutService
from .payment_gateway_strategy.strategies import (
    PaymentGatewayStrategy,
    resolve_gateway_from_request,
)

from config.cache import redis_client

######### RESOURCE DEPENDENCIES ##########




######### REPOSITORY DEPENDENCIES ###########

def get_payment_repository() -> idempotence_repo.PaymentRepository:
    return idempotence_repo.PaymentRepository(
        redis_client=redis_client
    )


######### SERVICE DEPENDENCIES ###########

def get_payment_gateway_service() -> idempotence_services.PaymentGatewayService:
    return idempotence_services.PaymentGatewayService()

def get_idempotent_payment_service() -> idempotence_services.IdempotentPaymentService:
    return idempotence_services.IdempotentPaymentService()

def get_payment_services() -> idempotence_services.PaymentServices:
    return idempotence_services.PaymentServices(
        repository=get_payment_repository(),
        payment_gateway_services=get_payment_gateway_service(),
    )


######### STRATEGY PATTERN (PAYMENT GATEWAYS) ###########


def get_payment_gateway_strategy(request: Request) -> PaymentGatewayStrategy:
    return resolve_gateway_from_request(request)


def get_checkout_service(
    gateway: Annotated[
        PaymentGatewayStrategy, Depends(get_payment_gateway_strategy)
    ],
) -> CheckoutService:
    return CheckoutService(gateway=gateway)


CheckoutServiceDep = Annotated[CheckoutService, Depends(get_checkout_service)]