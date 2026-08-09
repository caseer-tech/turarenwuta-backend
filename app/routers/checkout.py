import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticket
from app.schemas import CheckoutInitRequest, CheckoutInitResponse, CapacityResponse, TicketStatusResponse

router = APIRouter(tags=["checkout"])

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"


def _sold_count(db: Session) -> int:
    return db.query(Ticket).filter(Ticket.payment_status == "paid").count()


@router.get("/tickets/capacity", response_model=CapacityResponse)
def get_capacity(db: Session = Depends(get_db)):
    sold = _sold_count(db)
    remaining = max(settings.capacity - sold, 0)
    return CapacityResponse(
        capacity=settings.capacity,
        sold=sold,
        remaining=remaining,
        sold_out=remaining == 0,
    )


@router.post("/checkout/init", response_model=CheckoutInitResponse)
def init_checkout(payload: CheckoutInitRequest, db: Session = Depends(get_db)):
    if _sold_count(db) >= settings.capacity:
        raise HTTPException(status_code=409, detail="Event is sold out")

    ticket_ref = f"TWC2-{uuid.uuid4().hex[:8].upper()}"

    ticket = Ticket(
        ticket_ref=ticket_ref,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        payment_method=payload.payment_method,
        payment_status="pending",
        amount_kobo=settings.ticket_price_kobo,
        paystack_reference=ticket_ref,
    )
    db.add(ticket)
    db.commit()

    channels = ["card"] if payload.payment_method == "card" else ["bank_transfer"]

    resp = httpx.post(
        PAYSTACK_INIT_URL,
        headers={"Authorization": f"Bearer {settings.paystack_secret_key}"},
        json={
            "email": payload.email,
            "amount": settings.ticket_price_kobo,
            "reference": ticket_ref,
            "channels": channels,
            "callback_url": settings.frontend_success_url,
            "metadata": {"name": payload.name, "phone": payload.phone},
        },
        timeout=15,
    )

    if resp.status_code != 200 or not resp.json().get("status"):
        db.delete(ticket)
        db.commit()
        raise HTTPException(status_code=502, detail="Could not start payment with Paystack")

    data = resp.json()["data"]
    return CheckoutInitResponse(ticket_ref=ticket_ref, authorization_url=data["authorization_url"])


@router.get("/tickets/status/{ticket_ref}", response_model=TicketStatusResponse)
def get_ticket_status(ticket_ref: str, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_ref == ticket_ref).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketStatusResponse(
        ticket_ref=ticket.ticket_ref,
        payment_status=ticket.payment_status,
        name=ticket.name,
    )
