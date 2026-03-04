"""
Admin Panel admin registration.
"""

from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "description", "actor", "created_at"]
    list_filter = ["action", "entity_type", "created_at"]
    search_fields = ["description", "actor__email", "actor__full_name"]
    readonly_fields = ["id", "actor", "action", "entity_type", "entity_id", "description", "metadata", "created_at"]
    ordering = ["-created_at"]
