"""
Admin configuration for the chatrooms app.
Provides full monitoring access for admins — read-only for messages.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import ChatRoom, Message


class MessageInline(admin.TabularInline):
    """Inline readonly display of messages within a chatroom."""

    model = Message
    extra = 0
    readonly_fields = ("id", "sender", "message_type", "text", "file", "created_at", "is_deleted")
    fields = ("id", "sender", "message_type", "text", "file", "created_at", "is_deleted")
    ordering = ("-created_at",)
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.action(description=_("Disable selected chatrooms"))
def disable_chatrooms(modeladmin, request, queryset):
    """Admin action to bulk-disable chatrooms."""
    queryset.filter(is_active=True).update(is_active=False, disabled_at=timezone.now())


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin interface for chatrooms."""

    list_display = ("id", "sender", "receiver", "is_active", "created_at", "disabled_at")
    list_filter = ("is_active", "created_at")
    search_fields = (
        "sender__email",
        "sender__username",
        "receiver__email",
        "receiver__username",
    )
    readonly_fields = ("id", "sender", "receiver", "request", "created_at", "disabled_at")
    raw_id_fields = ("sender", "receiver", "request")
    inlines = [MessageInline]
    ordering = ("-created_at",)
    actions = [disable_chatrooms]

    def has_add_permission(self, request):
        return False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for messages — read-only monitoring."""

    list_display = ("id", "chatroom", "sender", "message_type", "short_text", "created_at", "is_deleted")
    list_filter = ("message_type", "is_deleted", "created_at")
    search_fields = (
        "sender__email",
        "sender__username",
        "text",
    )
    readonly_fields = ("id", "chatroom", "sender", "message_type", "text", "file", "created_at")
    ordering = ("-created_at",)

    def short_text(self, obj):
        if obj.text:
            return obj.text[:50] + ("..." if len(obj.text) > 50 else "")
        return "-"

    short_text.short_description = _("Text Preview")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow toggling is_deleted for moderation only
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False
