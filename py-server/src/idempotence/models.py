import enum
from sqlalchemy import Column, Integer, String, JSON, Enum, DateTime

from config import db


class PaymentProcessingStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class IdempotentPaymentStatus(db.Base):
    __tablename__ = "idempotent_payment_status"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(PaymentProcessingStatus), nullable=False)
    amount = Column(Integer)
    response = Column(JSON)
    started_at = Column(DateTime)


class PaymentRecordStatus(str, enum.Enum):
    UNPROCESSED = "UNPROCESSED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class PaymentRecord(db.Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, unique=True, index=True, nullable=True)
    status = Column(Enum(PaymentRecordStatus), nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)