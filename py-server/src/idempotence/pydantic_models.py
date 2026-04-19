from pydantic import BaseModel
from typing import Optional



class PayRequestPayload(BaseModel):
    order_id: str
    amount: float
    payment_but_not_logger_err: bool


class GenerateOrderIdPayload(BaseModel):
    amount: float