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
    # Hard stop server-side. Never trust a frontend "tickets remaining" counter alone.
    # NOTE: at very high simultaneous demand right at the cap, two people could both pass
    # this check before either finishes paying (only "paid" tickets count against the cap,
    # by design, so an abandoned checkout never blocks a real ticket). For 500 tickets and
    # the traffic you're expecting this is a fine trade-off. If you ever run a much bigger,
    # bigger-rush event, add a short-lived "reservation" row instead of just checking here.
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
        # Roll back the pending ticket row so it doesn't sit around forever as noise.
        db.delete(ticket)
        db.commit()
        raise HTTPException(status_code=502, detail="Could not start payment with Paystack")

    data = resp.json()["data"]
    return CheckoutInitResponse(ticket_ref=ticket_ref, authorization_url=data["authorization_url"])


@router.get("/tickets/status/{ticket_ref}", response_model=TicketStatusResponse)
def get_ticket_status(ticket_ref: str, db: Session = Depends(get_db)):
    # Used by the page the buyer lands on after Paystack redirects them back.
    # The webhook is what actually confirms payment (see webhook.py) — this endpoint
    # just lets the frontend show a real status instead of a blind "check your email".
    ticket = db.query(Ticket).filter(Ticket.ticket_ref == ticket_ref).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return TicketStatusResponse(
        ticket_ref=ticket.ticket_ref,
        payment_status=ticket.payment_status,
        name=ticket.name,
    )
