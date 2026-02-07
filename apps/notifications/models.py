"""
Notification models for Tramper.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Notification model for Tramper.
    Stores notifications for users about various events.
    """

    CATEGORY_CHOICES = [
        ("platform", _("Platform")),
        ("traveler", _("Traveler")),
        ("shopping", _("Shopping")),
        ("shipment_request", _("Shipment Request")),
        ("shipment_sent", _("Shipment Sent")),
        ("other", _("Other")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("user"),
        help_text=_("User who receives this notification"),
    )

    title = models.CharField(
        max_length=255,
        verbose_name=_("title"),
    )

    message = models.TextField(
        verbose_name=_("message"),
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
        verbose_name=_("category"),
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name=_("is read"),
    )

    # Optional reference to related objects
    request_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("request ID"),
        help_text=_("ID of related request, if any"),
    )

    shipment_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("shipment ID"),
        help_text=_("ID of related shipment, if any"),
    )

    trip_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("trip ID"),
        help_text=_("ID of related trip, if any"),
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("timestamp"),
    )

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.title} - {self.user}"
