"""
Password reset email module for Tramper.
Sends password reset email with token.
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

logger = logging.getLogger(__name__)


def send_password_reset_email(user, token):
    """
    Send password reset email with token.
    
    Args:
        user: User model instance
        token: Password reset token string
    """
    current_language = get_language()
    
    try:
        subject = _("Password Reset Request - Tramper")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email
        
        # Build reset URL (frontend should handle this route)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "token": token,
            "reset_url": reset_url,
            "site_name": "Tramper",
            "expiry_hours": 24,
        }
        
        # Render plain text email
        text_content = render_to_string(
            "emails/password_reset.txt",
            context,
        )
        
        # Render HTML email
        html_content = render_to_string(
            "emails/password_reset.html",
            context,
        )
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email],
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Password reset email sent to {to_email}")
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
    
    finally:
        # Restore language
        activate(current_language)
