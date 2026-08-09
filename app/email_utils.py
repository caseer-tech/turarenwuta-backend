import base64

import httpx

from app.config import settings

RESEND_URL = "https://api.resend.com/emails"


def send_ticket_email(to_email: str, name: str, ticket_ref: str, pdf_bytes: bytes) -> None:
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>You're in, {name}!</h2>
      <p>Your ticket for <strong>Turaren Wuta Carnival 2.0</strong> is confirmed
      &mdash; it's attached to this email as a PDF.</p>
      <ul>
        <li><strong>Date:</strong> Saturday, 31 October 2026, 2:00 PM &ndash; 6:00 PM</li>
        <li><strong>Venue:</strong> A-Class Events Centre, Abuja</li>
        <li><strong>Ticket Ref:</strong> {ticket_ref}</li>
      </ul>
      <p>Show the QR code on your ticket at the entrance. Please don't share it
      &mdash; it's tied to this ticket and can only be used once.</p>
      <p style="color:#888;font-size:12px;">No refunds. Bring the attached PDF
      or a screenshot of it on the day.</p>
    </div>
    """

    payload = {
        "from": settings.from_email,
        "to": [to_email],
        "subject": "Your Turaren Wuta Carnival 2.0 Ticket",
        "html": html,
        "attachments": [
            {
                "filename": f"{ticket_ref}.pdf",
                "content": base64.b64encode(pdf_bytes).decode(),
            }
        ],
    }

    headers = {"Authorization": f"Bearer {settings.resend_api_key}"}
    resp = httpx.post(RESEND_URL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
