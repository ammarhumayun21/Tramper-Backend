import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Complaint(models.Model):
    STATUS_CHOICES = [
        ("open", _("Open")),
        ("in_progress", _("In Progress")),
        ("resolved", _("Resolved")),
        ("closed", _("Closed")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )
    admin_response = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.user}"
