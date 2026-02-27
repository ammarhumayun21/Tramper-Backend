"""
Shipment models for Tramper.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from core.models import Location


class Category(models.Model):
    """
    Category model for shipment items.
    Defines available categories for items to be shipped.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("name"),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("description"),
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("icon"),
        help_text=_("Icon name or emoji for the category"),
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
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Dimension(models.Model):
    """
    Dimension model for shipment items.
    Stores height, width, length with unit.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("height"),
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("width"),
    )

    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("length"),
    )

    unit = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        default="cm",
        verbose_name=_("unit"),
        help_text=_("Measurement unit (e.g., cm, inches)"),
    )

    class Meta:
        verbose_name = _("dimension")
        verbose_name_plural = _("dimensions")

    def __str__(self):
        if self.height and self.width and self.length:
            return f"{self.height}x{self.width}x{self.length} {self.unit or ''}"
        return f"Dimension {self.id}"


class Shipment(models.Model):
    """
    Shipment model for Tramper.
    Represents a shipment request from a sender.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("in_transit", _("In Transit")),
        ("delivered", _("Delivered")),
        ("received", _("Received")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_shipments",
        verbose_name=_("sender"),
    )

    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivered_shipments",
        verbose_name=_("traveler"),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("notes"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name=_("status"),
    )

    from_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="shipments_from",
        verbose_name=_("from location"),
    )

    to_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="shipments_to",
        verbose_name=_("to location"),
    )

    travel_date = models.DateTimeField(
        verbose_name=_("travel date"),
    )

    reward = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("reward"),
        help_text=_("Reward amount for delivery"),
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
        verbose_name = _("shipment")
        verbose_name_plural = _("shipments")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.from_location} → {self.to_location}"


class ShipmentItem(models.Model):
    """
    Shipment item model.
    Represents individual items within a shipment.
    """

    WEIGHT_UNIT_CHOICES = [
        ("kg", _("Kilograms")),
        ("lbs", _("Pounds")),
        ("g", _("Grams")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("shipment"),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )

    link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("link"),
        help_text=_("Link to product or item details"),
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="shipment_items",
        verbose_name=_("category"),
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("quantity"),
    )

    single_item_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("single item price"),
    )

    single_item_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("single item weight"),
    )

    weight_unit = models.CharField(
        max_length=10,
        choices=WEIGHT_UNIT_CHOICES,
        default="kg",
        verbose_name=_("weight unit"),
    )

    dimensions = models.ForeignKey(
        Dimension,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shipment_items",
        verbose_name=_("dimensions"),
    )

    image_urls = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("image URLs"),
        help_text=_("Array of image URLs stored in S3"),
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
        verbose_name = _("shipment item")
        verbose_name_plural = _("shipment items")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.quantity}x) - {self.shipment.name}"

    @property
    def total_price(self):
        """Calculate total price for this item."""
        return self.single_item_price * self.quantity

    @property
    def total_weight(self):
        """Calculate total weight for this item."""
        return self.single_item_weight * self.quantity
