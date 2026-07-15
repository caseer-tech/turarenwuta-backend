import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_ref = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)

    payment_method = Column(String, nullable=False)  # "card" | "bank_transfer"
    payment_status = Column(String, nullable=False, default="pending")  # pending | paid | failed
    amount_kobo = Column(Integer, nullable=False)

    paystack_reference = Column(String, unique=True, index=True, nullable=False)

    qr_token = Column(String, nullable=True)
    checked_in = Column(Boolean, nullable=False, default=False)
    checked_in_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
