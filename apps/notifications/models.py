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


class DeviceToken(models.Model):
    """
    Stores FCM device tokens per user.

    One user can have multiple devices (phone, tablet, web browser).
    A single token is globally unique — if a device switches users
    (re-login), the existing record is reassigned via upsert.
    """

    DEVICE_TYPE_CHOICES = [
        ("ios", _("iOS")),
        ("android", _("Android")),
        ("web", _("Web")),
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
        related_name="device_tokens",
        verbose_name=_("user"),
        help_text=_("User who owns this device token"),
    )

    token = models.CharField(
        max_length=500,
        unique=True,
        verbose_name=_("FCM token"),
        help_text=_("Firebase Cloud Messaging registration token"),
    )

    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPE_CHOICES,
        verbose_name=_("device type"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("is active"),
        help_text=_("Inactive tokens are skipped during push. Set to False on send failure."),
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
        verbose_name = _("device token")
        verbose_name_plural = _("device tokens")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"], name="idx_devicetoken_user_active"),
        ]

    def __str__(self):
        return f"{self.device_type} token for {self.user} ({'active' if self.is_active else 'inactive'})"

