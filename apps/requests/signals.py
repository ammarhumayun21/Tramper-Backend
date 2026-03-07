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
