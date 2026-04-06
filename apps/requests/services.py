"""
Request services for Tramper.
Handles QR code generation for delivery confirmation.
"""

import io
import secrets
import logging

import qrcode
from qrcode.image.pil import PilImage

from core.storage import s3_storage

logger = logging.getLogger(__name__)


def generate_delivery_qr_code(request_obj):
    """
    Generate a QR code for delivery confirmation and upload it to S3.

    The QR encodes a deep link URL containing the shipment ID and a secret
    token. The token is stored on the Request and validated when the sender
    scans the code to confirm delivery.

    Args:
        request_obj: The accepted Request instance (must have a shipment).

    Returns:
        str: S3 URL of the generated QR code image.
    """
    token = secrets.token_urlsafe(32)

    confirm_url = (
        f"https://tramper-dbaebde837de.herokuapp.com/api/v1/payments"
        f"/{request_obj.shipment_id}/confirm-delivery/"
        f"?token={token}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(confirm_url)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    filename = f"{request_obj.shipment_id}_{request_obj.id}.png"
    url = s3_storage.upload_bytes(
        buffer,
        folder="qr_codes",
        filename=filename,
        content_type="image/png",
    )

    request_obj.qr_code_url = url
    request_obj.qr_token = token
    request_obj.save(update_fields=["qr_code_url", "qr_token", "updated_at"])

    logger.info(
        "Generated delivery QR code for request %s (shipment %s).",
        request_obj.id,
        request_obj.shipment_id,
    )

    return url
