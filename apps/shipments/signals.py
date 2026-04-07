import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Shipment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Shipment)
def update_sender_shipment_count(sender, instance, **kwargs):
    """Update the sender's total_shipments when a shipment is delivered."""
    if instance.status == "delivered" and instance.sender_id:
        user = instance.sender
        user.total_shipments = Shipment.objects.filter(
            sender=user, status="delivered"
        ).count()
        user.save(update_fields=["total_shipments"])


@receiver(post_save, sender=Shipment)
def generate_qr_on_in_transit(sender, instance, **kwargs):
    """Generate delivery QR code when shipment transitions to in_transit."""
    if instance.status != "in_transit":
        return

    from apps.requests.models import Request
    from apps.requests.services import generate_delivery_qr_code

    accepted_request = Request.objects.filter(
        shipment=instance, status="accepted"
    ).first()

    if not accepted_request:
        logger.warning(
            "Shipment %s is in_transit but has no accepted request.", instance.id
        )
        return

    if accepted_request.qr_code_url:
        logger.info(
            "QR code already exists for request %s, skipping.", accepted_request.id
        )
        return

    try:
        url = generate_delivery_qr_code(accepted_request)
        logger.info("Generated QR code for request %s: %s", accepted_request.id, url)
    except Exception:
        logger.exception(
            "Failed to generate QR code for request %s", accepted_request.id
        )
