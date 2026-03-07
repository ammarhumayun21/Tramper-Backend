"""
Management command to backfill total_trips, total_shipments, and total_deals
on the User model from actual related objects.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.users.models import User
from apps.trips.models import Trip
from apps.shipments.models import Shipment
from apps.requests.models import Request


class Command(BaseCommand):
    help = "Backfill user counters (total_trips, total_shipments, total_deals) from actual DB records."

    def handle(self, *args, **options):
        users = User.objects.all()
        updated = 0

        for user in users.iterator():
            trips = Trip.objects.filter(traveler=user, status="completed").count()
            shipments = Shipment.objects.filter(sender=user, status="delivered").count()
            deals = Request.objects.filter(
                Q(sender=user) | Q(receiver=user),
                status="accepted",
            ).count()

            changed = False
            if user.total_trips != trips:
                user.total_trips = trips
                changed = True
            if user.total_shipments != shipments:
                user.total_shipments = shipments
                changed = True
            if user.total_deals != deals:
                user.total_deals = deals
                changed = True

            if changed:
                user.save(update_fields=["total_trips", "total_shipments", "total_deals"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Backfilled counters for {updated} users."))
