from pydantic import BaseModel
from typing import Optional



class PayRequestPayload(BaseModel):
    paid_to: str
    amount: float
    fake_error: Optional[bool]