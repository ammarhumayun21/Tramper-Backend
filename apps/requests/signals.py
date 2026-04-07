from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Request


@receiver(post_save, sender=Request)
def update_deals_count_on_accept(sender, instance, **kwargs):
    """Update total_deals for both sender and receiver when a request is accepted."""
    if instance.status == "accepted":
        for user in [instance.sender, instance.receiver]:
            user.total_deals = Request.objects.filter(
                Q(sender=user) | Q(receiver=user),
                status="accepted",
            ).count()
            user.save(update_fields=["total_deals"])


@receiver(post_save, sender=Request)
def update_shipment_on_accept(sender, instance, **kwargs):
    """Update shipment traveler and reward when a request is accepted."""
    if instance.status != "accepted" or not instance.shipment:
        return

    shipment = instance.shipment

    # Skip if shipment already has a traveler assigned (already processed)
    if shipment.traveler and shipment.status == "accepted":
        return

    # Determine traveler based on who sent the request
    if instance.sender == shipment.sender:
        # Shipment owner sent the request → traveler is the receiver
        shipment.traveler = instance.receiver
    else:
        # Traveler sent the request → traveler is the sender
        shipment.traveler = instance.sender

    shipment.status = "accepted"
    # Update reward to the negotiated price (counter offer or original)
    shipment.reward = instance.current_price
    shipment.save(update_fields=["traveler", "status", "reward"])
