"""
Email utility helpers for Tramper.
Provides logo attachment and background sending.
"""

import logging
import threading
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

LOGO_PATH = Path(settings.BASE_DIR) / "templates" / "logo.png"


def attach_logo(email_message):
    """
    Attach the Tramper logo as an inline CID image to an EmailMultiAlternatives.

    Args:
        email_message: EmailMultiAlternatives instance
    """
    try:
        if LOGO_PATH.exists():
            with open(LOGO_PATH, "rb") as f:
                logo_data = f.read()
            logo_image = MIMEImage(logo_data, _subtype="png")
            logo_image.add_header("Content-ID", "<logo>")
            logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
            email_message.attach(logo_image)
    except Exception as e:
        logger.warning(f"Failed to attach logo to email: {str(e)}")


def create_email(subject, to_email, text_content, html_content, from_email=None):
    """
    Create an EmailMultiAlternatives with HTML and inline logo.

    Args:
        subject: Email subject
        to_email: Recipient email (string or list)
        text_content: Plain text body
        html_content: HTML body
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)

    Returns:
        EmailMultiAlternatives instance ready to send
    """
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    if isinstance(to_email, str):
        to_email = [to_email]

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to_email,
    )
    email.attach_alternative(html_content, "text/html")
    email.mixed_subtype = "related"
    attach_logo(email)
    return email


def send_email_background(subject, to_email, text_content, html_content, from_email=None):
    """
    Send an email with logo in a background thread.

    Args:
        subject: Email subject
        to_email: Recipient email (string or list)
        text_content: Plain text body
        html_content: HTML body
        from_email: Sender email
    """
    def _send():
        try:
            email = create_email(subject, to_email, text_content, html_content, from_email)
            email.send(fail_silently=False)
            logger.info(f"Background email '{subject}' sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send background email '{subject}' to {to_email}: {str(e)}")

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
