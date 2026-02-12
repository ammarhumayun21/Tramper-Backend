"""
Trip models for Tramper.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from core.models import Location, Airline


class TripCapacity(models.Model):
    """
    Capacity model for trips.
    Tracks total and used weight with unit.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    total_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("total weight"),
    )

    used_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("used weight"),
    )

    unit = models.CharField(
        max_length=10,
        default="kg",
        verbose_name=_("unit"),
        help_text=_("Weight unit (e.g., kg, lbs)"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("trip capacity")
        verbose_name_plural = _("trip capacities")

    def __str__(self):
        return f"{self.used_weight}/{self.total_weight} {self.unit}"

    @property
    def available_weight(self):
        """Calculate available weight."""
        return self.total_weight - self.used_weight

    @property
    def is_full(self):
        """Check if capacity is full."""
        return self.used_weight >= self.total_weight


class Trip(models.Model):
    """
    Trip model for Tramper.
    Represents a traveler's trip offering delivery capacity.
    """

    MODE_CHOICES = [
        ("trip", _("Trip")),
        ("train", _("Train")),
        ("ship", _("Ship")),
        ("bus", _("Bus")),
    ]

    STATUS_CHOICES = [
        ("valid", _("Valid")),
        ("invalid", _("Invalid")),
    ]

    CATEGORY_CHOICES = [
        ("documents", _("Documents")),
        ("electronics", _("Electronics")),
        ("clothing", _("Clothing")),
        ("food", _("Food")),
        ("medicine", _("Medicine")),
        ("fragile", _("Fragile")),
        ("other", _("Other")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name=_("traveler"),
    )

    first_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name=_("first name"),
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name=_("last name"),
    )

    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default="trip",
        verbose_name=_("mode of transport"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="valid",
        verbose_name=_("status"),
    )

    from_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="trips_from",
        verbose_name=_("from location"),
    )

    to_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="trips_to",
        verbose_name=_("to location"),
    )

    booking_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("booking reference"),
        help_text=_("Booking or ticket reference number"),
    )

    departure_date = models.DateField(
        verbose_name=_("departure date"),
    )

    departure_time = models.TimeField(
        verbose_name=_("departure time"),
    )

    capacity = models.OneToOneField(
        TripCapacity,
        on_delete=models.CASCADE,
        related_name="trip",
        verbose_name=_("capacity"),
    )

    transport_details = models.TextField(
        blank=True,
        verbose_name=_("transport details"),
        help_text=_("Additional details about the transport"),
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        blank=True,
        verbose_name=_("preferred category"),
        help_text=_("Preferred category of items to carry"),
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
        help_text=_("Additional notes or requirements"),
    )

    airline = models.ForeignKey(
        Airline,
        on_delete=models.SET_NULL,
        related_name="trips",
        null=True,
        blank=True,
        verbose_name=_("airline"),
        help_text=_("Airline for air travel"),
    )

    pickup_availability_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("pickup availability start date"),
        help_text=_("Start date for pickup availability"),
    )

    pickup_availability_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("pickup availability end date"),
        help_text=_("End date for pickup availability"),
    )

    meeting_points = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("meeting points"),
        help_text=_("List of meeting point locations"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("trip")
        verbose_name_plural = _("trips")
        ordering = ["-departure_date", "-departure_time"]

    def __str__(self):
        return f"{self.from_location} → {self.to_location} ({self.departure_date})"

    def save(self, *args, **kwargs):
        """Override save to populate names from traveler if not provided."""
        if not self.first_name and self.traveler:
            self.first_name = self.traveler.full_name.split()[0] if self.traveler.full_name else self.traveler.username
        if not self.last_name and self.traveler and self.traveler.full_name:
            name_parts = self.traveler.full_name.split()
            self.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        super().save(*args, **kwargs)

