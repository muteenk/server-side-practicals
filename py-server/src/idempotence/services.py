import asyncio
from datetime import datetime
from fastapi import HTTPException
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
    def get_payment_status_by_order_id(
        self, 
        order_id: str,
        db_session: Session
    ):
        payment_record = (
            db_session.query(PaymentRecord)
            .filter_by(order_id=order_id)
            .first()
        )
        if not payment_record:
            raise ValueError(404, "Payment record does not exist")
        return payment_record.status
    
    def generate_order_id(
        self,
        amount: float,
        db_session: Session
    ):
        generated_order_id = f"order_{time.time()}"
        payment_record = PaymentRecord(
            order_id=generated_order_id,
            amount=amount,
            status=PaymentRecordStatus.UNPROCESSED.value,
            created_at=datetime.now()
        )
        db_session.add(payment_record)
        db_session.commit()
        return generated_order_id

    async def fake_payment_processing(
        self,
        order_id: str,
        amount: float,
        db_session: Session
    ):
        await asyncio.sleep(3)  # fake processing state
        generate_payment_id = f"pay_{time.time()}"
        payment_record = (
            db_session.query(PaymentRecord)
            .filter_by(order_id=order_id)
            .first()
        )
        if amount != payment_record.amount:
            raise ValueError(400, "Invalid Amount")
            
        payment_record.payment_id = generate_payment_id
        payment_record.status = PaymentRecordStatus.SUCCESS.value

        db_session.commit()
        return generate_payment_id
