from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
import time, asyncio

import db as db_session

app = FastAPI()

@app.get("/")
def root():
    return {"message": "API running"}


class PayRequestPayload(BaseModel):
    paid_to: str
    amount: float

@app.post("/pay")
async def pay_route(request: Request, payload: PayRequestPayload):
    idempotency_key = request.headers.get('idempotency-key')
    if not idempotency_key:
        return HTTPException(400, "Idempotency key required !")
    db = db_session.SessionLocal()
    try:
        payment_obj = db_session.Payment(
            idempotency_key=idempotency_key,
            status=db_session.Status.PROCESSING.value,
            amount=payload.amount
        )
        db.add(payment_obj)
        db.commit()
        await asyncio.sleep(2)
        result = {
            "payment_id": f"pay_{int(time.time())}",
            "status": db_session.Status.SUCCESS.value, 
            "message": "Payment Processed"
        }
        payment_obj.status = db_session.Status.SUCCESS.value
        payment_obj.response = result
        db.commit()
        return result
    except IntegrityError as e:
        db.rollback()
        existing = (
            db.query(db_session.Payment)
            .filter_by(idempotency_key=idempotency_key).first()
        )
        if existing.status == db_session.Status.SUCCESS.value:
            return existing.response
        elif existing.status == db_session.Status.FAILED.value:
            return HTTPException(status_code=400, detail="Failed")
        elif existing.status == db_session.Status.PROCESSING.value:
            return HTTPException(status_code=409, detail="Processing")
        return HTTPException(500, str(e))
    except Exception as e:
        existing = (
            db.query(db_session.Payment)
            .filter_by(idempotency_key=idempotency_key).first()
        )
        existing.status = db_session.Status.FAILED.value
        return HTTPException(500, f"An error occurred while processing: {str(e)}")
    finally:
        db.close()
    