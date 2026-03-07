"""
Admin Panel models for Tramper.
Activity log for tracking all system events.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ActivityLog(models.Model):
    """
    Activity log model for tracking all CRUD operations
    and status changes across the platform.
    """

    ACTION_CHOICES = [
        ("created", _("Created")),
        ("updated", _("Updated")),
        ("deleted", _("Deleted")),
        ("status_changed", _("Status Changed")),
    ]

    ENTITY_TYPE_CHOICES = [
        ("trip", _("Trip")),
        ("shipment", _("Shipment")),
        ("request", _("Request")),
        ("user", _("User")),
        ("verification", _("Verification")),
        ("chatroom", _("Chatroom")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name=_("actor"),
        help_text=_("User who performed the action. Null for system events."),
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_("action"),
    )

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        verbose_name=_("entity type"),
    )

    entity_id = models.UUIDField(
        verbose_name=_("entity ID"),
        help_text=_("ID of the affected entity."),
    )

    description = models.TextField(
        verbose_name=_("description"),
        help_text=_("Human-readable description of the activity."),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("metadata"),
        help_text=_("Additional data: old/new status, changed fields, etc."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("activity log")
        verbose_name_plural = _("activity logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["entity_type", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.entity_type}: {self.description[:80]}"
