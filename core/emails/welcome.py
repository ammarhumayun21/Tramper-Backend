"""
Welcome email module for Tramper.
Sends welcome email on user registration.
"""

import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

logger = logging.getLogger(__name__)


def send_welcome_email(user):
    """
    Send welcome email to newly registered user.
    
    Args:
        user: User model instance
    """
    current_language = get_language()
    
    try:
        subject = _("Welcome to Tramper!")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email
        
        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "site_name": "Tramper",
        }
        
        # Render plain text email
        text_content = render_to_string(
            "emails/welcome.txt",
            context,
        )
        
        # Render HTML email
        html_content = render_to_string(
            "emails/welcome.html",
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
        
        logger.info(f"Welcome email sent to {to_email}")
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
    
    finally:
        # Restore language
        activate(current_language)
