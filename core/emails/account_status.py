"""
Account status email module for Tramper.
Sends email when admin activates or deactivates a user account.
"""

import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from .utils import send_email_background

logger = logging.getLogger(__name__)


def send_account_status_email(user, is_active):
    """
    Send account status email when admin toggles user active/inactive (background).

    Args:
        user: User model instance
        is_active: bool - True if account was activated, False if deactivated
    """
    try:
        status_display = "Activated" if is_active else "Deactivated"

        subject = _(f"Account {status_display} - Tramper")
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "is_active": is_active,
            "status_display": status_display,
            "site_name": "Tramper",
        }

        text_content = render_to_string("emails/account_status.txt", context)
        html_content = render_to_string("emails/account_status.html", context)

        send_email_background(subject, to_email, text_content, html_content)

        logger.info(f"Account status email ({status_display}) queued for {to_email}")

    except Exception as e:
        logger.error(f"Failed to queue account status email to {user.email}: {str(e)}")
