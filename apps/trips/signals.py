from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Trip


@receiver(post_save, sender=Trip)
def update_traveler_trip_count(sender, instance, **kwargs):
    """Update the traveler's total_trips when a trip is completed."""
    if instance.status == "completed" and instance.traveler_id:
        user = instance.traveler
        user.total_trips = Trip.objects.filter(
            traveler=user, status="completed"
        ).count()
        user.save(update_fields=["total_trips"])
