import asyncio
from sqlalchemy.orm import Session
import time

from .models import (
    IdempotentPaymentStatus, PaymentProcessingStatus,
    PaymentRecord, PaymentRecordStatus
)

class IdempotentPaymentService:
    def get_idempotent_payment(
        self,
        idempotency_key: str,
        db_session: Session
    ) -> IdempotentPaymentStatus:
        existing = (
            db_session.query(IdempotentPaymentStatus)
            .filter_by(idempotency_key=idempotency_key).first()
        )
        return existing

    def create_new_payment_status(
        self,
        idempotency_key: str,
        status: PaymentProcessingStatus,
        amount: float,
        db_session: Session
    ) -> IdempotentPaymentStatus:
        payment_obj = IdempotentPaymentStatus(
            idempotency_key=idempotency_key,
            status=status,
            amount=amount
        )
        db_session.add(payment_obj)
        db_session.commit()
        return payment_obj
    
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
        return payment_object


class PaymentGatewayService:
    async def fake_payment_processing(
        self,
        amount: float,
        db_session: Session
    ):
        await asyncio.sleep(2)  # fake processing state
        generate_payment_id = f"pay_{time.time()}"
        payment_record = PaymentRecord(
            payment_id=generate_payment_id,
            amount=amount,
            status=PaymentRecordStatus.SUCCESS.value
        )
        db_session.add(payment_record)
        db_session.commit()
        return generate_payment_id
