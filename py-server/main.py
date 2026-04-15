from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

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
    try:
        db = db_session.SessionLocal()
        idempotency_key = request.headers.get('idempotency-key')
        if not idempotency_key:
            return HTTPException(400, "Idempotency key required !")
        
        payment_obj = db_session.Payment(
            idempotency_key=idempotency_key,
            status=db_session.Status.PROCESSING.value,
            amount=payload.amount
        )
        db.add(payment_obj)
        db.commit()
        return {"message": f"{idempotency_key}"}
    except IntegrityError as e:
        db.rollback()
        return HTTPException(400, str(e))
    except Exception as e:
        return HTTPException(500, f"An error occurred while processing: {str(e)}")
    