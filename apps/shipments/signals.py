from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Shipment


@receiver(post_save, sender=Shipment)
def update_sender_shipment_count(sender, instance, **kwargs):
    """Update the sender's total_shipments when a shipment is delivered."""
    if instance.status == "delivered" and instance.sender_id:
        user = instance.sender
        user.total_shipments = Shipment.objects.filter(
            sender=user, status="delivered"
        ).count()
        user.save(update_fields=["total_shipments"])
