from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.exc import IntegrityError
from typing import Annotated

from .models import IdempotentPaymentStatus, PaymentProcessingStatus
from .pydantic_models import PayRequestPayload, GenerateOrderIdPayload
from .services import IdempotentPaymentService, PaymentGatewayService

from config import db
from src import dependencies


router = APIRouter()


@router.post("/idempotence/generate-order")
def generate_order_id(
    payload: GenerateOrderIdPayload,
    payment_gateway_service: Annotated[
        PaymentGatewayService,
        Depends(dependencies.get_payment_gateway_service)
    ]
):
    db_session = db.SessionLocal()
    try:
        order_id = payment_gateway_service.generate_order_id(
            payload.amount, 
            db_session
        )
        return {
            "status": 201,
            "order_id": order_id
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/idempotence/pay")
async def idempotent_payment_route(
    request: Request, 
    payload: PayRequestPayload,
    payment_gateway_service: Annotated[
        PaymentGatewayService,
        Depends(dependencies.get_payment_gateway_service)
    ],
    payment_service: Annotated[
        IdempotentPaymentService, 
        Depends(dependencies.get_idempotent_payment_service)
    ]
):
    idempotency_key = request.headers.get('idempotency-key')
    if not idempotency_key:
        return HTTPException(400, "Idempotency key required !")
    db_session = db.SessionLocal()
    try:
        payment_obj = payment_service.create_new_payment_status(
            idempotency_key=idempotency_key,
            status=PaymentProcessingStatus.PROCESSING.value,
            amount=payload.amount,
            order_id=payload.order_id,
            started_at=datetime.now(),
            db_session=db_session
        )
        payment_id = await payment_gateway_service.fake_payment_processing(
            order_id=payload.order_id, 
            amount=payload.amount,
            db_session=db_session
        )
        if payload.payment_but_not_logger_err:
            raise ValueError("Error occurred after payment was made !!!")
        result = {
            "payment_id": payment_id,
            "status": PaymentProcessingStatus.SUCCESS.value, 
            "message": "Payment Processed"
        }
        payment_obj = payment_service.update_idempotent_payment_status(
            payment_object=payment_obj,
            status=PaymentProcessingStatus.SUCCESS.value,
            response=result,
            db_session=db_session
        )
        return result
    except IntegrityError as e:
        db_session.rollback()
        existing = payment_service.get_idempotent_payment(idempotency_key, db_session)
        payment_status_map = {
            PaymentProcessingStatus.PROCESSING.value: 409,
            PaymentProcessingStatus.FAILED.value: 400
        }
        if existing.status == PaymentProcessingStatus.SUCCESS.value:
            return existing.response
        status_code = payment_status_map[existing.status]
        if status_code:
            raise HTTPException(status_code=status_code, detail=existing.status)
        raise HTTPException(500, str(e))
    except Exception as e:
        db_session.rollback()
        existing = payment_service.get_idempotent_payment(idempotency_key, db_session)
        existing.status = PaymentProcessingStatus.FAILED.value
        db_session.commit()
        raise HTTPException(500, f"An error occurred while processing: {str(e)}")
    finally:
        db_session.close()
    