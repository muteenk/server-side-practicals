from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from typing import Annotated

from .models import PaymentRecordStatus, PaymentProcessingStatus
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
    finally:
        db_session.close()


def _status_eq(row_status, expected: PaymentProcessingStatus) -> bool:
    v = getattr(row_status, "value", row_status)
    return v == expected.value


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
    idempotency_key = request.headers.get("idempotency-key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency key required")

    db_session = db.SessionLocal()
    payment_obj = None

    try:
        try:
            payment_obj = payment_service.create_new_payment_status(
                idempotency_key=idempotency_key,
                status=PaymentProcessingStatus.PROCESSING.value,
                amount=int(payload.amount),
                order_id=payload.order_id,
                started_at=datetime.now(),
                db_session=db_session
            )
        except IntegrityError:
            db_session.rollback()
            print("Duplicate request detected")
            existing = payment_service.get_idempotent_payment(
                idempotency_key, db_session
            )
            if not existing:
                raise HTTPException(
                    status_code=500,
                    detail="Could not resolve idempotent payment row"
                )

            if _status_eq(existing.status, PaymentProcessingStatus.SUCCESS):
                print("Returning stored response")
                return existing.response

            if _status_eq(existing.status, PaymentProcessingStatus.PROCESSING):
                try:
                    pr = payment_gateway_service.get_payment_record_by_order_id(
                        order_id=existing.order_id,
                        db_session=db_session
                    )
                except HTTPException:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "status": "PROCESSING",
                            "message": "Already processing"
                        }
                    )
                if pr.status == PaymentRecordStatus.SUCCESS:
                    result = {
                        "payment_id": pr.payment_id,
                        "status": PaymentProcessingStatus.SUCCESS.value,
                        "message": "Payment Processed"
                    }
                    payment_service.update_idempotent_payment_status(
                        payment_object=existing,
                        status=PaymentProcessingStatus.SUCCESS.value,
                        response=result,
                        db_session=db_session
                    )
                    print("Returning stored response")
                    return result
                return JSONResponse(
                    status_code=409,
                    content={
                        "status": "PROCESSING",
                        "message": "Already processing"
                    }
                )

            fail_body = existing.response or {
                "status": PaymentProcessingStatus.FAILED.value,
                "message": "Previous attempt failed"
            }
            return JSONResponse(status_code=400, content=fail_body)

        print("Processing new request")
        try:
            payment_id = await payment_gateway_service.fake_payment_processing(
                order_id=payload.order_id,
                amount=payload.amount,
                db_session=db_session
            )
        except Exception as e:
            payment_service.update_idempotent_payment_status(
                payment_object=payment_obj,
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
        payment_service.update_idempotent_payment_status(
            payment_object=payment_obj,
            status=PaymentProcessingStatus.SUCCESS.value,
            response=result,
            db_session=db_session
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing: {e!s}"
        )
    finally:
        db_session.close()
