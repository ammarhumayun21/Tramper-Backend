"""
Core models for Tramper.
Shared models used across multiple apps.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Location(models.Model):
    """
    Location model for storing airport/location information.
    Used across trips and shipments for origin and destination.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    country = models.CharField(
        max_length=100,
        verbose_name=_("country"),
    )

    city = models.CharField(
        max_length=100,
        verbose_name=_("city"),
    )

    airport_name = models.CharField(
        max_length=255,
        verbose_name=_("airport name"),
    )

    iata_code = models.CharField(
        max_length=10,
        verbose_name=_("IATA code"),
        help_text=_("3-letter airport code (e.g., JFK, LAX, LHR)"),
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
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ["country", "city"]

    def __str__(self):
        return f"{self.city}, {self.country} ({self.iata_code})"
