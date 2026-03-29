"""
Payment signals for Tramper.
Automatically initiates payment when shipment is accepted.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.shipments.models import Shipment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Shipment)
def initiate_payment_on_acceptance(sender, instance, **kwargs):
    """
    When a shipment status changes to 'accepted', automatically
    create a payment intent via Ziina.
    """
    if instance.status != "accepted":
        return

    # Check if update_fields was used and status wasn't updated
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "status" not in update_fields:
        return

    # Avoid circular imports
    from apps.payments.services.payment_service import payment_service
    from apps.payments.services.ziina import ZiinaAPIError

    try:
        payment = payment_service.initiate_payment(instance)
        logger.info(
            "Auto-initiated payment %s for shipment %s on acceptance.",
            payment.id,
            instance.id,
        )
    except ZiinaAPIError as e:
        logger.error(
            "Failed to auto-initiate payment for shipment %s: %s",
            instance.id,
            str(e),
        )
    except ValueError as e:
        logger.warning(
            "Skipped payment initiation for shipment %s: %s",
            instance.id,
            str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error initiating payment for shipment %s: %s",
            instance.id,
            str(e),
        )
