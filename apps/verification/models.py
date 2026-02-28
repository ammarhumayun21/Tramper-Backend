"""
Verification center models for Tramper.
Stores user identity verification documents for admin review.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class VerificationRequest(models.Model):
    """
    Verification request model.
    Stores user-submitted identity documents for admin verification.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
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
        related_name="verification_requests",
        verbose_name=_("user"),
    )

    id_card_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("ID card number"),
        help_text=_("Number written on the ID card"),
    )

    id_card_front_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("ID card front image URL"),
        help_text=_("URL of uploaded front side of ID card"),
    )

    id_card_back_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("ID card back image URL"),
        help_text=_("URL of uploaded back side of ID card"),
    )

    selfie_with_id_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("selfie with ID image URL"),
        help_text=_("URL of uploaded selfie holding ID card"),
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("phone number"),
        help_text=_("Phone number submitted for verification"),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name=_("status"),
    )

    admin_notes = models.TextField(
        blank=True,
        verbose_name=_("admin notes"),
        help_text=_("Notes from admin during review"),
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_verifications",
        verbose_name=_("reviewed by"),
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("reviewed at"),
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
        verbose_name = _("verification request")
        verbose_name_plural = _("verification requests")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Verification for {self.user.email} - {self.status}"
