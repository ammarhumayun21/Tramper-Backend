"""
Chatroom service layer for Tramper.
Handles chatroom creation, disabling, and related business logic.
"""

from django.utils import timezone

from .models import ChatRoom


def create_chatroom(request_obj):
    """
    Create a chatroom for an accepted request.
    Uses get_or_create to ensure idempotency (one chatroom per request).
    """
    chatroom, created = ChatRoom.objects.get_or_create(
        request=request_obj,
        defaults={
            "sender": request_obj.sender,
            "receiver": request_obj.receiver,
        },
    )
    return chatroom, created

  
def disable_chatroom(chatroom):
    """Disable a chatroom and set the disabled timestamp."""
    chatroom.is_active = False
    chatroom.disabled_at = timezone.now()
    chatroom.save(update_fields=["is_active", "disabled_at"])


def disable_chatrooms_for_shipment(shipment):
    """
    Disable all active chatrooms linked to a shipment via its requests.
    Called when a shipment reaches 'received' status.
    """
    chatrooms = ChatRoom.objects.filter(
        request__shipment=shipment,
        is_active=True,
    )
    now = timezone.now()
    chatrooms.update(is_active=False, disabled_at=now)
