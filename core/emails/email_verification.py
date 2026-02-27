"""
Email verification module for Tramper.
Sends email with verification link when user registers.
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

logger = logging.getLogger(__name__)


def create_email_verification_token(user):
    """
    Create an email verification token for the given user.

    Args:
        user: User model instance

    Returns:
        EmailVerificationToken instance
    """
    from apps.users.models import EmailVerificationToken

    # Invalidate previous tokens
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)

    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=72)

    verification_token = EmailVerificationToken.objects.create(
        user=user,
        token=token,
        expires_at=expires_at,
    )

    return verification_token


def send_email_verification(user):
    """
    Send email verification link to user.

    Args:
        user: User model instance
    """
    current_language = get_language()

    try:
        verification_token = create_email_verification_token(user)

        verification_url = (
            f"{settings.FRONTEND_URL}/verify-email?token={verification_token.token}"
        )

        subject = _("Verify your email - Tramper")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "verification_url": verification_url,
            "site_name": "Tramper",
            "expiry_hours": 72,
        }

        text_content = render_to_string("emails/email_verification.txt", context)
        html_content = render_to_string("emails/email_verification.html", context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Email verification sent to {to_email}")

    except Exception as e:
        logger.error(f"Failed to send email verification to {user.email}: {str(e)}")

    finally:
        activate(current_language)
