"""
Core models for Tramper.
Shared models used across multiple apps.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    """
    ISO 3166 country reference data.
    All 249 countries with codes, region info, and flag emoji.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_("name"),
    )

    alpha_2 = models.CharField(
        max_length=2,
        unique=True,
        verbose_name=_("alpha-2 code"),
        help_text=_("ISO 3166-1 alpha-2 code (e.g., US, GB, AE)"),
    )

    alpha_3 = models.CharField(
        max_length=3,
        unique=True,
        verbose_name=_("alpha-3 code"),
        help_text=_("ISO 3166-1 alpha-3 code (e.g., USA, GBR, ARE)"),
    )

    numeric_code = models.CharField(
        max_length=3,
        blank=True,
        verbose_name=_("numeric code"),
        help_text=_("ISO 3166-1 numeric code"),
    )

    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("region"),
        help_text=_("Continent/region (e.g., Europe, Asia, Americas)"),
    )

    sub_region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("sub-region"),
        help_text=_("Sub-region (e.g., Northern Europe, Southern Asia)"),
    )

    flag_emoji = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("flag emoji"),
    )

    has_airports = models.BooleanField(
        default=False,
        verbose_name=_("has airports"),
        help_text=_("Whether this country has at least one airport in the database"),
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
        verbose_name = _("country")
        verbose_name_plural = _("countries")
        ordering = ["name"]

    def __str__(self):
        return f"{self.flag_emoji} {self.name} ({self.alpha_2})"


class City(models.Model):
    """
    City reference data.
    Derived from airports dataset — every city that has at least one airport.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_("name"),
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="cities",
        verbose_name=_("country"),
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("latitude"),
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("longitude"),
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
        verbose_name = _("city")
        verbose_name_plural = _("cities")
        ordering = ["country__name", "name"]
        unique_together = [("name", "country")]

    def __str__(self):
        return f"{self.name}, {self.country.name}"


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

    # Structured FK references (populated by populate_world_data)
    city_ref = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="airports",
        verbose_name=_("city reference"),
        help_text=_("Structured reference to City model"),
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("latitude"),
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("longitude"),
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


class Airline(models.Model):
    """
    Airline model for storing airline information.
    Used for trip transport details.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )

    iata_code = models.CharField(
        max_length=3,
        unique=True,
        verbose_name=_("IATA code"),
        help_text=_("2-letter airline code (e.g., AA, BA, EK)"),
    )

    country = models.CharField(
        max_length=100,
        verbose_name=_("country"),
        help_text=_("Headquarters country"),
    )

    # Structured FK reference (populated by populate_world_data)
    country_ref = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="airlines",
        verbose_name=_("country reference"),
        help_text=_("Structured reference to Country model"),
    )

    logo_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("logo URL"),
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
        verbose_name = _("airline")
        verbose_name_plural = _("airlines")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.iata_code})"
