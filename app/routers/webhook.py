import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticket
from app.qr_utils import generate_qr_token
from app.ticket_pdf import build_ticket_pdf
from app.email_utils import send_ticket_email

logger = logging.getLogger("turaren.webhook")

router = APIRouter(tags=["webhook"])


def _verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(
        settings.paystack_secret_key.encode(), raw_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    if event != "charge.success":
        return {"received": True}

    data = payload["data"]
    reference = data["reference"]

    ticket = db.query(Ticket).filter(Ticket.paystack_reference == reference).first()
    if not ticket:
        logger.warning("Webhook for unknown reference: %s", reference)
        return {"received": True, "note": "no matching ticket"}

    if ticket.payment_status == "paid":
        return {"received": True, "note": "already processed"}

    ticket.payment_status = "paid"
    ticket.qr_token = generate_qr_token(ticket.ticket_ref)
    db.commit()

    qr_data = f"{ticket.ticket_ref}:{ticket.qr_token}"

    try:
        pdf_bytes = build_ticket_pdf(
            name=ticket.name,
            ticket_ref=ticket.ticket_ref,
            qr_data=qr_data,
        )
        send_ticket_email(ticket.email, ticket.name, ticket.ticket_ref, pdf_bytes)
        ticket.email_sent = True
        ticket.email_error = None
        db.commit()
    except Exception as e:
        # The payment is real and the ticket IS paid regardless of what happens
        # here — an email/PDF problem must never make Paystack think the charge
        # failed. But unlike before, this failure is now visible (Render logs)
        # and recorded (queryable + re-sendable via /admin/resend-ticket).
        logger.error(
            "Failed to send ticket email for %s (%s): %s",
            ticket.ticket_ref, ticket.email, e,
        )
        ticket.email_sent = False
        ticket.email_error = str(e)[:500]
        db.commit()

    return {"received": True}
