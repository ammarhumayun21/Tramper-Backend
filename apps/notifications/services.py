"""
Notification service for creating notifications.
"""

from .models import Notification


class NotificationService:
    """
    Service class for creating notifications.
    Call these methods from views/signals when events occur.
    """

    @staticmethod
    def create(user, title, message, category="other", request_id=None, shipment_id=None, trip_id=None):
        """Create a notification for a user."""
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            category=category,
            request_id=request_id,
            shipment_id=shipment_id,
            trip_id=trip_id,
        )

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
    def notify_platform(user, title, message):
        """Send a platform notification to a user."""
        return NotificationService.create(
            user=user,
            title=title,
            message=message,
            category="platform",
        )

    @staticmethod
    def notify_shopping(user, title, message, shipment_id=None):
        """Send a shopping notification to a user."""
        return NotificationService.create(
            user=user,
            title=title,
            message=message,
            category="shopping",
            shipment_id=shipment_id,
        )

    @staticmethod
    def notify_traveler(user, title, message, trip_id=None):
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
