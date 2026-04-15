from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import db

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
        idempotency_key = request.headers.get('idempotency-key')
        if not idempotency_key:
            return HTTPException(400, "Idempotency key required !")
        return {"message": f"{idempotency_key}"}
    except Exception as e:
        return HTTPException(500, f"An error occurred while processing: {str(e)}")
    