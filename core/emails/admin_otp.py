"""
Admin OTP email module for Tramper.
Sends OTP email for admin login verification.
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

from .utils import attach_logo

logger = logging.getLogger(__name__)


def send_admin_otp_email(user_email: str, otp: str, user_name: str) -> bool:
    """
    Send Admin login OTP email.
    
    Args:
        user_email: Admin's email address
        otp: 6-digit OTP code
        user_name: Admin's name
    """
    current_language = get_language()
    
    try:
        subject = _("Your Admin Login OTP code")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user_email
        
        context = {
            "otp": otp,
            "user_name": user_name,
            "site_name": "Tramper",
        }
        
        # Render plain text email
        text_content = render_to_string(
            "emails/admin_otp.txt",
            context,
        )
        
        # Render HTML email
        html_content = render_to_string(
            "emails/admin_otp.html",
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
        email.mixed_subtype = "related"
        attach_logo(email)
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Admin OTP email sent to {to_email}")
        success = True
        
        
    except Exception as e:
        logger.error(f"Failed to send admin OTP email to {user_email}: {str(e)}")
        success = False
    
    finally:
        # Restore language
        activate(current_language)
        
    return success
