"""
Complaint email modules for Tramper.
Handles new complaint notifications, status updates, and admin replies.
"""

import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from apps.users.models import User
from .utils import send_email_background

logger = logging.getLogger(__name__)


def send_new_complaint_admin_email(complaint):
    """
    Send email to all superadmin users when a new complaint is submitted (background).

    Args:
        complaint: Complaint model instance (with user, subject, description)
    """
    try:
        admin_emails = list(
            User.objects.filter(is_superuser=True, is_active=True)
            .values_list("email", flat=True)
        )
        if not admin_emails:
            logger.warning("No active superadmin users to notify about new complaint")
            return

        complainant = complaint.user
        subject = _("New Complaint Received - Tramper")

        for admin_email in admin_emails:
            context = {
                "user": type("obj", (object,), {"email": admin_email})(),
                "complainant_name": complainant.full_name or complainant.username,
                "complainant_email": complainant.email,
                "complaint_subject": complaint.subject,
                "complaint_description": complaint.description,
                "created_at": complaint.created_at.strftime("%B %d, %Y at %I:%M %p") if complaint.created_at else "",
                "site_name": "Tramper",
            }

            text_content = render_to_string("emails/new_complaint_admin.txt", context)
            html_content = render_to_string("emails/new_complaint_admin.html", context)

            send_email_background(subject, admin_email, text_content, html_content)

        logger.info(f"New complaint notification queued for {len(admin_emails)} admin(s)")

    except Exception as e:
        logger.error(f"Failed to queue new complaint admin email: {str(e)}")


def send_complaint_status_email(complaint):
    """
    Send email to the complaint creator when status changes (background).

    Args:
        complaint: Complaint model instance (with user, subject, status, admin_response)
    """
    try:
        user = complaint.user
        status_map = {
            "open": "Open",
            "in_progress": "In Progress",
            "resolved": "Resolved",
            "closed": "Closed",
        }
        status_display = status_map.get(complaint.status, complaint.status.title())

        subject = _(f"Complaint {status_display} - Tramper")
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "complaint_subject": complaint.subject,
            "status": complaint.status,
            "status_display": status_display,
            "admin_response": complaint.admin_response or "",
            "updated_at": complaint.updated_at.strftime("%B %d, %Y at %I:%M %p") if complaint.updated_at else "",
            "site_name": "Tramper",
        }

        text_content = render_to_string("emails/complaint_status.txt", context)
        html_content = render_to_string("emails/complaint_status.html", context)

        send_email_background(subject, to_email, text_content, html_content)

        logger.info(f"Complaint status email ({status_display}) queued for {to_email}")

    except Exception as e:
        logger.error(f"Failed to queue complaint status email to {user.email}: {str(e)}")


def send_complaint_reply_email(complaint, email_subject, email_message):
    """
    Send formatted admin reply email to the complaint user (background).

    Args:
        complaint: Complaint model instance
        email_subject: Subject line for the email
        email_message: Message body from admin
    """
    try:
        user = complaint.user
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "complaint_subject": complaint.subject,
            "email_subject": email_subject,
            "email_message": email_message,
            "site_name": "Tramper",
        }

        text_content = render_to_string("emails/complaint_reply.txt", context)
        html_content = render_to_string("emails/complaint_reply.html", context)

        send_email_background(email_subject, to_email, text_content, html_content)

        logger.info(f"Complaint reply email queued for {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to queue complaint reply email to {complaint.user.email}: {str(e)}")
        return False
