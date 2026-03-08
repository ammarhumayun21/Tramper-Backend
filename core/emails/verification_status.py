"""
Verification status email module for Tramper.
Sends email when admin approves or rejects a verification request.
"""

import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from .utils import send_email_background

logger = logging.getLogger(__name__)


def send_verification_status_email(verification_request):
    """
    Send verification status email to user after admin review (background).

    Args:
        verification_request: VerificationRequest model instance (with status, admin_notes, reviewed_at)
    """
    try:
        user = verification_request.user
        is_approved = verification_request.status == "approved"
        status_display = "Approved" if is_approved else "Rejected"

        subject = _(f"Verification {status_display} - Tramper")
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "is_approved": is_approved,
            "status_display": status_display,
            "admin_notes": verification_request.admin_notes or "",
            "reviewed_at": verification_request.reviewed_at.strftime("%B %d, %Y at %I:%M %p") if verification_request.reviewed_at else "",
            "site_name": "Tramper",
        }

        text_content = render_to_string("emails/verification_status.txt", context)
        html_content = render_to_string("emails/verification_status.html", context)

        send_email_background(subject, to_email, text_content, html_content)

        logger.info(f"Verification status email ({status_display}) queued for {to_email}")

    except Exception as e:
        logger.error(f"Failed to queue verification status email to {verification_request.user.email}: {str(e)}")
