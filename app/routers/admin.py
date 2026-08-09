from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticket
from app.ticket_pdf import build_ticket_pdf
from app.email_utils import send_ticket_email

router = APIRouter(tags=["admin"])


@router.post("/admin/resend-ticket/{ticket_ref}")
def resend_ticket(
    ticket_ref: str,
    x_admin_key: str = Header(default=None),
    db: Session = Depends(get_db),
):
    if x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ticket = db.query(Ticket).filter(Ticket.ticket_ref == ticket_ref).first()
    if not ticket or ticket.payment_status != "paid":
        raise HTTPException(status_code=404, detail="No paid ticket with that reference")

    qr_data = f"{ticket.ticket_ref}:{ticket.qr_token}"
    pdf_bytes = build_ticket_pdf(name=ticket.name, ticket_ref=ticket.ticket_ref, qr_data=qr_data)
    send_ticket_email(ticket.email, ticket.name, ticket.ticket_ref, pdf_bytes)

    ticket.email_sent = True
    ticket.email_error = None
    db.commit()

    return {"resent": True, "ticket_ref": ticket.ticket_ref, "email": ticket.email}
