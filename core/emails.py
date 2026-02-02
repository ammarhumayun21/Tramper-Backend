"""
Email utilities for sending transactional emails.
Supports both plain text and HTML templates.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Centralized service for sending emails.
    Supports templated HTML and plain text emails.
    """

    @staticmethod
    def send_email(
        subject: str,
        recipient_list: list,
        text_content: str,
        html_content: str = None,
        from_email: str = None,
    ) -> bool:
        """
        Send email with optional HTML content.

        Args:
            subject: Email subject
            recipient_list: List of recipient email addresses
            text_content: Plain text email body
            html_content: Optional HTML email body
            from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)

        Returns:
            bool: True if email sent successfully
        """
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL

        try:
            if html_content:
                # Send as multipart with both plain text and HTML
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=recipient_list,
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)
            else:
                # Send plain text email
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=from_email,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
            return False

    @staticmethod
    def send_templated_email(
        subject: str,
        recipient_list: list,
        text_template: str,
        html_template: str = None,
        context: dict = None,
        from_email: str = None,
    ) -> bool:
        """
        Send email using Django templates.

        Args:
            subject: Email subject
            recipient_list: List of recipient emails
            text_template: Path to plain text template
            html_template: Path to HTML template
            context: Context dictionary for template rendering
            from_email: Sender email

        Returns:
            bool: True if email sent successfully
        """
        if context is None:
            context = {}

        text_content = render_to_string(text_template, context)
        html_content = None

        if html_template:
            html_content = render_to_string(html_template, context)

        return EmailService.send_email(
            subject=subject,
            recipient_list=recipient_list,
            text_content=text_content,
            html_content=html_content,
            from_email=from_email,
        )


# Example usage functions
def send_welcome_email(user_email: str, user_name: str) -> bool:
    """Send welcome email to new user."""
    return EmailService.send_email(
        subject=str(_("Welcome to Tramper!")),
        recipient_list=[user_email],
        text_content=f"{_('Hello')} {user_name},\n\n{_('Welcome to Tramper!')}",
        html_content=f"<h1>{_('Welcome')}, {user_name}!</h1><p>{_('Welcome to Tramper!')}</p>",
    )


def send_password_reset_email(user_email: str, reset_token: str) -> bool:
    """Send password reset email."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    return EmailService.send_email(
        subject=str(_("Reset Your Password")),
        recipient_list=[user_email],
        text_content=f"{_('Click the link to reset your password')}: {reset_url}",
        html_content=f'<a href="{reset_url}">{_("Reset Password")}</a>',
    )
