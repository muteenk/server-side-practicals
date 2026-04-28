from datetime import datetime
import json
from redis import Redis
from sqlalchemy.orm import Session

from .models import (
    IdempotentPaymentStatus,
    PaymentProcessingStatus
)

from config.exceptions import ServerError


class PaymentRepository:
    """
        Methods to access payment related db operations
    """
    def __init__(self, redis_client: Redis):
        self.cache = redis_client

    def update_cached_payment_record(
        self,
        idempotency_key: str,
        status: str,
        response: dict,
        timestamp: datetime
    ):
        try:
            self.cache.set(idempotency_key, json.dumps({
                "status": status,
                "response": response,
                "timestamp": timestamp
            }), ex=84200)
        except Exception as e:
            raise ServerError("Failed to set cache", e)
        
    def create_new_payment_status(
        self,
        idempotency_key: str,
        status: PaymentProcessingStatus,
        amount: float,
        order_id: str,
        started_at: datetime,
        db_session: Session
    ) -> IdempotentPaymentStatus:
        payment_obj = IdempotentPaymentStatus(
            idempotency_key=idempotency_key,
            status=status,
            amount=amount,
            order_id=order_id,
            started_at=started_at
        )
        db_session.add(payment_obj)
        db_session.commit()
        self.cache.set(idempotency_key, json.dumps({
            "status": status,
            "response": {
                "status": status,
                "message": "Payment Processing"
            },
            "timestamp": started_at 
        }), nx=True, ex=84200)
        return payment_obj

    def get_idempotent_payment_record(
        self,
        idempotency_key: str,
        db_session: Session
    ) -> IdempotentPaymentStatus | None:
        return (
            db_session.query(IdempotentPaymentStatus)
            .filter_by(idempotency_key=idempotency_key).first()
        )
    
    def update_idempotent_payment_status(
        self,
        payment_object: IdempotentPaymentStatus,
        status: PaymentProcessingStatus | None,
        response: dict | None,
        db_session: Session
    ) -> IdempotentPaymentStatus:
        if status:
            payment_object.status = status
        if response:
            payment_object.response = response
        db_session.commit()
        self.update_cached_payment_record(
            idempotency_key=payment_object.idempotency_key,
            status=status,
            response=response,
            timestamp=datetime.now().isoformat()
        )
        return payment_object