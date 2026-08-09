import io
from pathlib import Path

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

TEMPLATE_PATH = Path(__file__).parent / "assets" / "ticket_template.jpg"

IMG_W, IMG_H = 1024, 1536
CREAM = (0.973, 0.933, 0.875)
GOLD = (0.94, 0.62, 0.125)
MAROON = (0.42, 0.05, 0.05)


def _img_to_pdf_y(img_y: float) -> float:
    return IMG_H - img_y


def _draw_vip_badge(c: canvas.Canvas) -> None:
    """Diagonal ribbon across the top-right corner. Only called for VIP tickets —
    reuses the same template file, no separate design asset needed."""
    c.saveState()
    c.translate(IMG_W - 110, IMG_H - 280)
    c.rotate(-45)
    c.setFillColorRGB(*GOLD)
    ribbon_w, ribbon_h = 300, 58
    c.rect(-ribbon_w / 2, -ribbon_h / 2, ribbon_w, ribbon_h, fill=1, stroke=0)
    c.setFillColorRGB(*MAROON)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(0, -11, "VIP")
    c.restoreState()


def build_ticket_pdf(name: str, ticket_ref: str, qr_data: str, is_vip: bool = False) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(IMG_W, IMG_H))

    c.drawImage(str(TEMPLATE_PATH), 0, 0, width=IMG_W, height=IMG_H)

    # --- QR code ---
    qr_img_buf = io.BytesIO()
    qrcode.make(qr_data).save(qr_img_buf, format="PNG")
    qr_img_buf.seek(0)
    c.drawImage(
        ImageReader(qr_img_buf),
        163,
        _img_to_pdf_y(1187 + 247),
        width=247,
        height=247,
        mask="auto",
    )

    # --- Attendee name ---
    c.setFillColorRGB(*CREAM)
    c.rect(288, _img_to_pdf_y(1140), 630, 90, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 30)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawString(300, _img_to_pdf_y(1092) - 10, name.upper())

    # --- Ticket ID ---
    c.setFillColorRGB(*CREAM)
    c.rect(520, _img_to_pdf_y(1336), 430, 1336 - 1248, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 26)
    c.setFillColorRGB(*MAROON)
    c.drawCentredString(735, _img_to_pdf_y(1307), ticket_ref)

    if is_vip:
        _draw_vip_badge(c)

    c.save()
    return buf.getvalue()
