import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Ticket
from app.qr_utils import verify_qr_token
from app.schemas import CheckinRequest, CheckinResponse

router = APIRouter(tags=["checkin"])


def require_staff(x_checkin_key: str | None = Header(default=None)) -> None:
    """Every check-in requires a dedicated secret; never reuse the admin credential."""
    if not settings.checkin_key:
        raise HTTPException(status_code=503, detail="Staff check-in is not configured")
    if not x_checkin_key or not hmac.compare_digest(x_checkin_key, settings.checkin_key):
        raise HTTPException(status_code=401, detail="Invalid staff access key")


@router.post("/checkin", response_model=CheckinResponse, dependencies=[Depends(require_staff)])
def checkin(payload: CheckinRequest, db: Session = Depends(get_db)):
    # The QR is a signed ticket_ref:token; do not accept the ticket_ref alone.
    if not verify_qr_token(payload.ticket_ref, payload.token):
        return CheckinResponse(valid=False, already_checked_in=False, message="Invalid ticket code")

    ticket = db.query(Ticket).filter(Ticket.ticket_ref == payload.ticket_ref).first()
    if (
        ticket is None
        or ticket.payment_status != "paid"
        or not ticket.qr_token
        or not hmac.compare_digest(ticket.qr_token, payload.token)
    ):
        return CheckinResponse(valid=False, already_checked_in=False, message="Ticket not found or unpaid")

    if ticket.checked_in:
        return CheckinResponse(
            valid=True,
            already_checked_in=True,
            name=ticket.name,
            message=f"Already checked in at {ticket.checked_in_at}",
        )

    # Atomic conditional update: only one scanner can change the same ticket
    # from unchecked to checked, even if both try at the same time.
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    changed = db.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket.id,
            Ticket.payment_status == "paid",
            Ticket.checked_in.is_(False),
        )
        .values(checked_in=True, checked_in_at=timestamp)
    ).rowcount
    db.commit()

    if changed == 1:
        return CheckinResponse(
            valid=True,
            already_checked_in=False,
            name=ticket.name,
            message="Checked in",
        )

    # Someone else admitted this ticket between the SELECT and the UPDATE.
    db.refresh(ticket)
    return CheckinResponse(
        valid=True,
        already_checked_in=True,
        name=ticket.name,
        message=f"Already checked in at {ticket.checked_in_at}",
    )
