"""
Trip status email module for Tramper.
Sends email when admin approves or rejects (cancels) a trip.
"""

import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from .utils import send_email_background

logger = logging.getLogger(__name__)


def send_trip_status_email(trip, is_approved):
    """
    Send trip status email when admin approves or cancels a trip (background).

    Args:
        trip: Trip model instance (with traveler, from_location, to_location)
        is_approved: bool - True if approved, False if cancelled
    """
    try:
        user = trip.traveler
        status_display = "Approved" if is_approved else "Cancelled"

        subject = _(f"Trip {status_display} - Tramper")
        to_email = user.email

        context = {
            "user": user,
            "full_name": user.full_name or user.username,
            "is_approved": is_approved,
            "status_display": status_display,
            "from_location": f"{trip.from_location.city}" if trip.from_location else "Unknown",
            "to_location": f"{trip.to_location.city}" if trip.to_location else "Unknown",
            "departure_date": trip.departure_date.strftime("%B %d, %Y") if trip.departure_date else "",
            "departure_time": trip.departure_time.strftime("%I:%M %p") if trip.departure_time else "",
            "mode": trip.get_mode_display() if hasattr(trip, "get_mode_display") else trip.mode,
            "site_name": "Tramper",
        }

        text_content = render_to_string("emails/trip_status.txt", context)
        html_content = render_to_string("emails/trip_status.html", context)

        send_email_background(subject, to_email, text_content, html_content)

        logger.info(f"Trip status email ({status_display}) queued for {to_email}")

    except Exception as e:
        logger.error(f"Failed to queue trip status email to {user.email}: {str(e)}")
