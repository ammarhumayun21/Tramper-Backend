"""
Admin configuration for notifications app.
"""

from django.contrib import admin
from .models import Notification, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notification model."""

    list_display = (
        "id",
        "user",
        "title",
        "category",
        "is_read",
        "timestamp",
    )
    list_filter = ("category", "is_read", "timestamp")
    search_fields = (
        "user__email",
        "user__first_name",
        "title",
        "message",
    )
    readonly_fields = ("id", "timestamp")
    raw_id_fields = ("user",)
    ordering = ("-timestamp",)
    
    actions = ["mark_as_read", "mark_as_unread"]

    @admin.action(description="Mark selected notifications as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected notifications as unread")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin for DeviceToken model (FCM push notification tokens)."""

    list_display = (
        "id",
        "user",
        "device_type",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("device_type", "is_active", "created_at")
    search_fields = (
        "user__email",
        "user__username",
        "token",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)

    actions = ["activate_tokens", "deactivate_tokens"]

    @admin.action(description="Activate selected device tokens")
    def activate_tokens(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deactivate selected device tokens")
    def deactivate_tokens(self, request, queryset):
        queryset.update(is_active=False)
