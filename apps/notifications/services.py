"""
Notification service for creating notifications and sending FCM push.

Every notification created through this service is:
  1. Saved to the database (always)
  2. Sent as an FCM push notification (async via Celery, if user preferences allow)
"""

import logging
from typing import Optional

from .models import Notification

logger = logging.getLogger(__name__)

# Category → UserSettings preference field mapping.
# None = always push (critical / transactional notifications).
PUSH_PREFERENCE_MAP = {
    "platform": None,  # System-level — always push
    "shipment_request": None,  # Transactional — always push
    "shipment_sent": None,  # Transactional — always push
    "traveler": "matchmaking_notifications_enabled",
    "shopping": "matchmaking_notifications_enabled",
    "other": None,  # Default — always push
}


class NotificationService:
    """
    Service class for creating notifications and triggering FCM push.
    Call these methods from views/signals when events occur.

    Usage:
        from apps.notifications.services import notification_service
        notification_service.notify_request_created(request_obj)
    """

    @staticmethod
    def create(
        user,
        title: str,
        message: str,
        category: str = "other",
        request_id=None,
        shipment_id=None,
        trip_id=None,
    ) -> Notification:
        """
        Create a notification for a user AND send FCM push (async via Celery).

        The DB record is always created. Push is gated by user preferences.
        """
        # 1. Always save to database
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            category=category,
            request_id=request_id,
            shipment_id=shipment_id,
            trip_id=trip_id,
        )

        # 2. Send FCM push if preferences allow
        if NotificationService._should_push(user, category):
            try:
                from .push import send_to_user

                data = {
                    "notification_id": str(notification.id),
                    "category": category,
                }
                if request_id:
                    data["request_id"] = str(request_id)
                if shipment_id:
                    data["shipment_id"] = str(shipment_id)
                if trip_id:
                    data["trip_id"] = str(trip_id)

                send_to_user(user, title, message, data=data)
            except Exception:
                logger.exception(
                    "Failed to queue FCM push for notification %s",
                    notification.id,
                )

        return notification

    @staticmethod
    def _should_push(user, category: str) -> bool:
        """
        Check if push notification should be sent based on user preferences.

        Returns True if:
          - The category has no preference gate (critical/transactional)
          - The user's settings allow it
          - The user has no settings record (default: allow)
        """
        pref_field = PUSH_PREFERENCE_MAP.get(category)
        if pref_field is None:
            return True  # No preference gate — always push

        try:
            settings_obj = user.settings
            return getattr(settings_obj, pref_field, True)
        except Exception:
            # No UserSettings record — default to push
            return True

    @staticmethod
    def notify_request_created(request_obj):
        """Notify receiver when a new request is created."""
        sender_name = request_obj.sender.full_name or request_obj.sender.username
        
        if request_obj.shipment:
            title = "New Shipment Request"
            message = f"{sender_name} has sent you a request for your shipment."
        else:
            title = "New Trip Request"
            message = f"{sender_name} has sent you a request for your trip."

        return NotificationService.create(
            user=request_obj.receiver,
            title=title,
            message=message,
            category="shipment_request",
            request_id=request_obj.id,
            shipment_id=request_obj.shipment_id,
            trip_id=request_obj.trip_id,
        )

    @staticmethod
    def notify_request_accepted(request_obj):
        """Notify sender when their request is accepted."""
        receiver_name = request_obj.receiver.full_name or request_obj.receiver.username
        
        title = "Request Accepted"
        message = f"{receiver_name} has accepted your request."

        return NotificationService.create(
            user=request_obj.sender,
            title=title,
            message=message,
            category="shipment_request",
            request_id=request_obj.id,
            shipment_id=request_obj.shipment_id,
            trip_id=request_obj.trip_id,
        )

    @staticmethod
    def notify_request_rejected(request_obj):
        """Notify sender when their request is rejected."""
        receiver_name = request_obj.receiver.full_name or request_obj.receiver.username
        
        title = "Request Rejected"
        message = f"{receiver_name} has declined your request."

        return NotificationService.create(
            user=request_obj.sender,
            title=title,
            message=message,
            category="shipment_request",
            request_id=request_obj.id,
            shipment_id=request_obj.shipment_id,
            trip_id=request_obj.trip_id,
        )

    @staticmethod
    def notify_counter_offer(counter_offer):
        """Notify the other party when a counter offer is made."""
        sender_name = counter_offer.sender.full_name or counter_offer.sender.username
        
        title = "New Counter Offer"
        message = f"{sender_name} has made a counter offer of {counter_offer.price}."

        return NotificationService.create(
            user=counter_offer.receiver,
            title=title,
            message=message,
            category="shipment_request",
            request_id=counter_offer.request_id,
        )

    @staticmethod
    def notify_shipment_status_change(shipment, old_status, new_status):
        """Notify shipment owner when status changes."""
        title = "Shipment Status Updated"
        message = f"Your shipment '{shipment.name}' status changed from {old_status} to {new_status}."

        return NotificationService.create(
            user=shipment.sender,
            title=title,
            message=message,
            category="shipment_sent",
            shipment_id=shipment.id,
        )

    @staticmethod
    def notify_trip_status_change(trip, old_status, new_status):
        """Notify trip owner when status changes."""
        title = "Trip Status Updated"
        message = f"Your trip status changed from {old_status} to {new_status}."

        return NotificationService.create(
            user=trip.traveler,
            title=title,
            message=message,
            category="traveler",
            trip_id=trip.id,
        )

    @staticmethod
    def notify_platform(user, title: str, message: str):
        """Send a platform notification to a user."""
        return NotificationService.create(
            user=user,
            title=title,
            message=message,
            category="platform",
        )

    @staticmethod
    def notify_shopping(user, title: str, message: str, shipment_id=None):
        """Send a shopping notification to a user."""
        return NotificationService.create(
            user=user,
            title=title,
            message=message,
            category="shopping",
            shipment_id=shipment_id,
        )

    @staticmethod
    def notify_traveler(user, title: str, message: str, trip_id=None):
        """Send a traveler notification to a user."""
        return NotificationService.create(
            user=user,
            title=title,
            message=message,
            category="traveler",
            trip_id=trip_id,
        )


# Singleton instance for easy access
notification_service = NotificationService()
