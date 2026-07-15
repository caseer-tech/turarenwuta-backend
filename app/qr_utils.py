import hashlib
import hmac
import base64
from io import BytesIO

import qrcode

from app.config import settings


def generate_qr_token(ticket_ref: str) -> str:
    """
    A short signed token tied to this ticket_ref only. Without knowing QR_SECRET,
    nobody can forge a valid token for a ticket_ref they guess or make up —
    this is what stops someone from just writing "TWC2-00000001" on a piece of
    paper and walking in.
    """
    digest = hmac.new(
        settings.qr_secret.encode(), ticket_ref.encode(), hashlib.sha256
    ).hexdigest()
    return digest[:16]


def verify_qr_token(ticket_ref: str, token: str) -> bool:
    expected = generate_qr_token(ticket_ref)
    return hmac.compare_digest(expected, token)


def build_checkin_url(base_url: str, ticket_ref: str, token: str) -> str:
    return f"{base_url}/checkin?ref={ticket_ref}&token={token}"


def generate_qr_png_base64(data: str) -> str:
    """Returns a base64-encoded PNG, ready to attach to an email."""
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
