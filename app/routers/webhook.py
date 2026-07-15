import hashlib
import hmac

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticket
from app.qr_utils import generate_qr_token, generate_qr_png_base64
from app.email_utils import send_ticket_email

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

    # This check is what stops anyone from POSTing a fake "payment successful"
    # request straight to your webhook URL and getting a free ticket.
    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    if event != "charge.success":
        # Ignore everything else (failed charges, transfers, etc.) — 200 so Paystack
        # doesn't keep retrying an event we don't need to act on.
        return {"received": True}

    data = payload["data"]
    reference = data["reference"]

    ticket = db.query(Ticket).filter(Ticket.paystack_reference == reference).first()
    if not ticket:
        # Shouldn't normally happen, but don't error — just acknowledge and log.
        return {"received": True, "note": "no matching ticket"}

    if ticket.payment_status == "paid":
        # Paystack can send the same event more than once — this makes the handler safe to re-run.
        return {"received": True, "note": "already processed"}

    ticket.payment_status = "paid"
    ticket.qr_token = generate_qr_token(ticket.ticket_ref)
    db.commit()

    qr_data = f"{ticket.ticket_ref}:{ticket.qr_token}"
    qr_png = generate_qr_png_base64(qr_data)

    try:
        send_ticket_email(ticket.email, ticket.name, ticket.ticket_ref, qr_png)
    except Exception:
        # Don't fail the webhook over an email hiccup — the ticket is paid and valid either way.
        # Log this in real deployment so you can manually resend if it happens.
        pass

    return {"received": True}
