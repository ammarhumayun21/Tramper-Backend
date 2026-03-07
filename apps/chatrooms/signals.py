"""
Signals for automatic chatroom creation and disabling.
- Creates chatroom when a request is accepted.
- Disables chatroom when the associated shipment is received.
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.requests.models import Request
from apps.shipments.models import Shipment
from . import services


def _cache_old_status(sender, instance, **kwargs):
    """Cache old status before save for change detection in post_save."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = getattr(old, "status", None)
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


pre_save.connect(_cache_old_status, sender=Request)
pre_save.connect(_cache_old_status, sender=Shipment)


@receiver(post_save, sender=Request)
def create_chatroom_on_request_accepted(sender, instance, **kwargs):
    """Create a chatroom when a request is accepted."""
    old_status = getattr(instance, "_old_status", None)
    if instance.status == "accepted" and old_status != "accepted":
        services.create_chatroom(instance)


@receiver(post_save, sender=Shipment)
def disable_chatroom_on_shipment_received(sender, instance, **kwargs):
    """Disable chatrooms when a shipment is marked as received."""
    old_status = getattr(instance, "_old_status", None)
    if instance.status == "received" and old_status != "received":
        services.disable_chatrooms_for_shipment(instance)
