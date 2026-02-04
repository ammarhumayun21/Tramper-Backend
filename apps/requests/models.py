"""
Request models for Tramper.
Handles requests between users for shipments and trips, with counter offer negotiation.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Request(models.Model):
    """
    Request model for Tramper.
    Represents a request from one user to another for a shipment or trip.
    
    Scenarios:
    - Shipment owner requests a traveler to carry their shipment
    - Traveler offers to carry someone's shipment
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("countered", _("Countered")),
        ("cancelled", _("Cancelled")),
        ("expired", _("Expired")),
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
        related_name="sent_requests",
        verbose_name=_("sender"),
        help_text=_("User who initiated the request"),
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_requests",
        verbose_name=_("receiver"),
        help_text=_("User who receives the request"),
    )

    shipment = models.ForeignKey(
        "shipments.Shipment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="requests",
        verbose_name=_("shipment"),
    )

    trip = models.ForeignKey(
        "trips.Trip",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="requests",
        verbose_name=_("trip"),
    )

    offered_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("offered price"),
        help_text=_("Price offered for the delivery"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name=_("status"),
    )

    message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("message"),
        help_text=_("Optional message with the request"),
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
        verbose_name = _("request")
        verbose_name_plural = _("requests")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request from {self.sender} to {self.receiver} - {self.status}"

    @property
    def latest_counter_offer(self):
        """Get the most recent counter offer."""
        return self.counter_offers.order_by("-created_at").first()

    @property
    def current_price(self):
        """Get the current negotiated price (latest counter offer or original)."""
        latest = self.latest_counter_offer
        return latest.price if latest else self.offered_price


class CounterOffer(models.Model):
    """
    Counter offer model for request negotiations.
    Allows back-and-forth price negotiation between sender and receiver.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="counter_offers",
        verbose_name=_("request"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_counter_offers",
        verbose_name=_("sender"),
        help_text=_("User who made this counter offer"),
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_counter_offers",
        verbose_name=_("receiver"),
        help_text=_("User who receives this counter offer"),
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("price"),
        help_text=_("Counter offer price"),
    )

    message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("message"),
        help_text=_("Optional message with the counter offer"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("counter offer")
        verbose_name_plural = _("counter offers")
        ordering = ["created_at"]

    def __str__(self):
        return f"Counter offer {self.price} on Request {self.request_id}"
