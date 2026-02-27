"""
Admin configuration for Verification Center.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import VerificationRequest


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    """Admin for verification requests."""

    list_display = [
        "user",
        "phone_number",
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    ]
    list_filter = ["status", "created_at", "reviewed_at"]
    search_fields = ["user__email", "user__username", "user__full_name", "phone_number"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user", "reviewed_by"]

    fieldsets = (
        (None, {"fields": ("id", "user", "phone_number", "status")}),
        (
            _("Documents"),
            {"fields": ("id_card_front_url", "id_card_back_url", "selfie_with_id_url")},
        ),
        (
            _("Review"),
            {"fields": ("admin_notes", "reviewed_by", "reviewed_at")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )
