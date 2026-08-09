import hashlib
import hmac
import base64
from io import BytesIO

import qrcode

from app.config import settings


def generate_qr_token(ticket_ref: str) -> str:
    digest = hmac.new(
        settings.qr_secret.encode(), ticket_ref.encode(), hashlib.sha256
    ).hexdigest()
    return digest[:16]


def verify_qr_token(ticket_ref: str, token: str) -> bool:
    expected = generate_qr_token(ticket_ref)
    return hmac.compare_digest(expected, token)


def generate_qr_png_base64(data: str) -> str:
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
