from .idempotence.services import IdempotentPaymentService, PaymentGatewayService




######### SERVICE DEPENDENCIES ###########

def get_payment_gateway_service() -> PaymentGatewayService:
    return PaymentGatewayService()

def get_idempotent_payment_service() -> IdempotentPaymentService:
    return IdempotentPaymentService()