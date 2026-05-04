import asyncio
from datetime import datetime
from fastapi import HTTPException
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import time

from .pydantic_models import CachedPayRequestPayload
from .models import (
    IdempotentPaymentStatus, PaymentProcessingStatus,
    PaymentRecord, PaymentRecordStatus
)
from .repository import (
    PaymentRepository
)

from config.exceptions import (
    ServerError,
    ValidationException,
    NotFoundException,
    ConflictException
)



class IdempotentPaymentHelpers:
    """
    Helper functions for Payment Controllers
    """
    def check_cache_for_response(
        self,
        cached_payment_payload: str
    ) -> tuple[str, dict]:
        try:
            cached_dict = json.loads(cached_payment_payload)
            cached_status = cached_dict.get('status')
            cached_resp = cached_dict.get('response')

            if cached_status not in [
                PaymentProcessingStatus.PROCESSING.value,
                PaymentProcessingStatus.SUCCESS.value,
                PaymentProcessingStatus.FAILED.value,
            ] or not cached_resp:
                raise HTTPException(500, f"Corrupted cache: {e}")
            
            return cached_status, cached_resp
        except Exception as e:
            raise HTTPException(500, f"Corrupted cache: {e}")


class IdempotentPaymentService:
    """
    PAYMENT METHODS OF OUR SERVER
    """
    def get_idempotent_payment(
        self,
        idempotency_key: str,
        db_session: Session
    ) -> IdempotentPaymentStatus | None:
        existing = (
            db_session.query(IdempotentPaymentStatus)
            .filter_by(idempotency_key=idempotency_key).first()
        )
        return existing

    def get_idempotent_payment_by_order_id(
        self,
        order_id: str,
        db_session: Session
    ) -> IdempotentPaymentStatus | None:
        return (
            db_session.query(IdempotentPaymentStatus)
            .filter_by(order_id=order_id)
            .first()
        )

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
    """
    PAYMENT GATEWAY SDK
    """
    def get_payment_record_by_order_id(
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
            raise HTTPException(404, "Payment record does not exist")
        return payment_record
    
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

        if not payment_record:
            payment_record = PaymentRecord(
                order_id=order_id,
                amount=amount,
                status=PaymentRecordStatus.UNPROCESSED.value,
                created_at=datetime.now()
            )
            db_session.add(payment_record)

        if payment_record.status == PaymentRecordStatus.SUCCESS:
            raise ValueError("Payment already processed")
        if int(amount) != int(payment_record.amount):
            raise ValueError("Invalid Amount")
            
        payment_record.payment_id = generate_payment_id
        payment_record.status = PaymentRecordStatus.SUCCESS

        db_session.commit()
        return generate_payment_id


class PaymentServices():
    """
        Core methods for payment routes
    """
    def __init__(
        self,
        repository: PaymentRepository,
        payment_gateway_services: PaymentGatewayService
    ):
        self.repo = repository
        self.payment_gateway = payment_gateway_services

    async def make_new_payment(
        self,
        idempotency_key: str,
        payload: CachedPayRequestPayload,
        db_session: Session
    ):
        try:
            initiated_payment_record = self.repo.create_new_payment_status(
                idempotency_key=idempotency_key,
                status=PaymentProcessingStatus.PROCESSING.value,
                amount=int(payload.amount),
                order_id=payload.order_id,
                started_at=datetime.now(),
                db_session=db_session
            )
        except IntegrityError as e:
            db_session.rollback()
            exists, response = self.fallback_payment_record_db_lookup(
                idempotency_key=idempotency_key,
                db_session=db_session
            )
            if not exists or not response:
                raise ServerError("Failed to create payment request", e)
            return response
        
        try:
            payment_id = await self.payment_gateway.fake_payment_processing(
                order_id=payload.order_id,
                amount=payload.amount,
                db_session=db_session
            )
        except Exception as e:
            self.repo.update_idempotent_payment_status(
                payment_object=initiated_payment_record,
                status=PaymentProcessingStatus.FAILED.value,
                response={
                    "status": PaymentProcessingStatus.FAILED.value,
                    "message": str(e)
                },
                db_session=db_session
            )
            raise HTTPException(status_code=400, detail=str(e))
        
        if payload.payment_but_not_logger_err:
            print("Simulated failure after payment")
            raise HTTPException(
                status_code=500,
                detail="Simulated failure after payment (success was persisted)"
            )

        result = {
            "payment_id": payment_id,
            "status": PaymentProcessingStatus.SUCCESS.value,
            "message": "Payment Processed"
        }
        self.repo.update_idempotent_payment_status(
            payment_object=initiated_payment_record,
            status=PaymentProcessingStatus.SUCCESS.value,
            response=result,
            db_session=db_session
        )

        return result

    def extract_cached_payload(
        self,
        cached_payment_payload: str
    ) -> tuple[str, dict, datetime]:
        try:
            cached_dict = json.loads(cached_payment_payload)
            cached_status = cached_dict.get('status')
            cached_resp = cached_dict.get('response')
            cached_timestamp = cached_dict.get('timestamp')

            if cached_status not in [
                PaymentProcessingStatus.PROCESSING.value,
                PaymentProcessingStatus.SUCCESS.value,
                PaymentProcessingStatus.FAILED.value,
            ] or not cached_resp:
                raise HTTPException(500, f"Corrupted cache: {e}")
            
            return cached_status, cached_resp, cached_timestamp
        except Exception as e:
            raise HTTPException(500, f"Corrupted cache: {e}")

    def check_cached_payment_record(
        self,
        cache: str,
        idempotency_key: str,
        db_session: Session
    ) -> tuple[bool, dict | None]:
        
        status, response, _ = self.extract_cached_payload(cache)

        if status == PaymentProcessingStatus.SUCCESS.value:
            return True, response
        elif status == PaymentProcessingStatus.FAILED.value:
            raise ValidationException("Payment Failed", details=response)
        
        return self.fallback_payment_record_db_lookup(
            idempotency_key=idempotency_key,
            db_session=db_session
        )

    def fallback_payment_record_db_lookup(
        self,
        idempotency_key: str,
        db_session: Session
    ) -> tuple[bool, dict | None]:
        existing = self.repo.get_idempotent_payment_record(
            idempotency_key, db_session
        )
        if not existing:
            return False, None
        
        if existing.status in [
            PaymentProcessingStatus.SUCCESS.value,
            PaymentProcessingStatus.FAILED.value
        ]:
            self.repo.update_cached_payment_record(
                idempotency_key=idempotency_key,
                status=existing.status,
                response=existing.response,
                timestamp=datetime.now().isoformat()
            )

            if existing.status == PaymentProcessingStatus.FAILED.value:
                raise ValidationException("Payment Failed", details=existing.response)
            return True, existing.response    
        else:
            return self.fallback_payment_gateway_record_lookup(
                order_id=existing.order_id,
                idempotent_payment_record=existing,
                db_session=db_session
            )
        
    def fallback_payment_gateway_record_lookup(
        self,
        order_id: str,
        idempotent_payment_record: IdempotentPaymentStatus,
        db_session: Session
    ) -> tuple[bool, dict | None]:
        payment_record = self.payment_gateway.get_payment_record_by_order_id(
            order_id=order_id,
            db_session=db_session
        )
        if not payment_record:
            raise NotFoundException("Payment record doesn't exist")
        
        if payment_record.status == PaymentRecordStatus.SUCCESS.value:
            result = {
                "payment_id": payment_record.payment_id,
                "status": PaymentProcessingStatus.SUCCESS.value,
                "message": "Payment Processed"
            }
            self.repo.update_idempotent_payment_status(
                payment_object=idempotent_payment_record,
                status=PaymentProcessingStatus.SUCCESS.value,
                response=result,
                db_session=db_session
            )
            return True, result
        elif payment_record.status == PaymentRecordStatus.FAILED.value:
            result = {
                "status": PaymentProcessingStatus.FAILED.value,
                "message": "Payment Failed"
            }
            self.repo.update_idempotent_payment_status(
                payment_object=idempotent_payment_record,
                status=PaymentProcessingStatus.FAILED.value,
                response=result,
                db_session=db_session
            )
            raise ValidationException("Payment Failed", result)
        else:
            raise ConflictException("Payment Processing", {
                "status": PaymentProcessingStatus.PROCESSING.value,
                "message": "Payment Processing"
            })
            

        
