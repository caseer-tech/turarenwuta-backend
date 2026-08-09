import io
from pathlib import Path

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Resolved relative to this file, not the process's working directory — avoids
# the exact kind of path-resolution bug that cost real time earlier in this
# project (requirements.txt / repo-root mismatches on Render).
TEMPLATE_PATH = Path(__file__).parent / "assets" / "ticket_template.png"

IMG_W, IMG_H = 1024, 1536  # must match the template file's actual pixel size
CREAM = (0.973, 0.933, 0.875)  # sampled from the template's card background


def _img_to_pdf_y(img_y: float) -> float:
    """The template's coordinates are measured from the top (like reading pixel
    positions off a screenshot). Reportlab measures from the bottom. This just
    flips between the two so every other coordinate below reads naturally."""
    return IMG_H - img_y


def build_ticket_pdf(name: str, ticket_ref: str, qr_data: str) -> bytes:
    """
    Composites the attendee's name, ticket reference, and a QR code onto the
    designed ticket template. Returns finished PDF bytes, ready to attach to
    an email — nothing is written to disk, so this is safe to call from a
    request handler with no cleanup required.
    """
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
    # The template has placeholder text baked into the background image itself,
    # so it has to be painted over before the real name goes on top.
    c.setFillColorRGB(*CREAM)
    c.rect(288, _img_to_pdf_y(1140), 630, 90, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 30)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.drawString(300, _img_to_pdf_y(1092) - 10, name.upper())

    # --- Ticket ID ---
    c.setFillColorRGB(*CREAM)
    c.rect(520, _img_to_pdf_y(1315), 430, 75, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 26)
    c.setFillColorRGB(0.42, 0.05, 0.05)
    c.drawCentredString(735, _img_to_pdf_y(1290), ticket_ref)

    c.save()
    return buf.getvalue()
