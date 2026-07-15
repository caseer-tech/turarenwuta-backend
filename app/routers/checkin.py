from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket
from app.qr_utils import verify_qr_token
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter(tags=["checkin"])


@router.post("/checkin", response_model=CheckinResponse)
def checkin(payload: CheckinRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.ticket_ref == payload.ticket_ref).first()

    if not ticket or ticket.payment_status != "paid":
        return CheckinResponse(valid=False, already_checked_in=False, message="Ticket not found or unpaid")

    if not verify_qr_token(ticket.ticket_ref, payload.token):
        return CheckinResponse(valid=False, already_checked_in=False, message="Invalid ticket code")

    if ticket.checked_in:
        return CheckinResponse(
            valid=True,
            already_checked_in=True,
            name=ticket.name,
            message=f"Already checked in at {ticket.checked_in_at}",
        )

    ticket.checked_in = True
    ticket.checked_in_at = datetime.utcnow()
    db.commit()

    return CheckinResponse(valid=True, already_checked_in=False, name=ticket.name, message="Checked in")
