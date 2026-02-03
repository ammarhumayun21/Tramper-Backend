"""
Admin configuration for Trip models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Trip, TripCapacity


class TripCapacityInline(admin.StackedInline):
    """Inline admin for trip capacity."""
    model = TripCapacity
    can_delete = False
    verbose_name_plural = _("Capacity")
    fields = ["total_weight", "used_weight", "unit"]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    """Admin for trips."""

    list_display = [
        "from_location",
        "to_location",
        "traveler",
        "departure_date",
        "departure_time",
        "mode",
        "status",
        "created_at",
    ]
    list_filter = ["status", "mode", "category", "departure_date", "created_at"]
    search_fields = [
        "from_location",
        "to_location",
        "first_name",
        "last_name",
        "traveler__email",
        "traveler__username",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "departure_date"
    ordering = ["-departure_date", "-departure_time"]

    fieldsets = (
        (None, {"fields": ("id", "traveler", "status")}),
        (
            _("Trip Details"),
            {
                "fields": (
                    "from_location",
                    "to_location",
                    "departure_date",
                    "departure_time",
                    "mode",
                    "category",
                )
            },
        ),
        (
            _("Traveler Information"),
            {"fields": ("first_name", "last_name")},
        ),
        (
            _("Additional Information"),
            {"fields": ("transport_details", "notes")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )


@admin.register(TripCapacity)
class TripCapacityAdmin(admin.ModelAdmin):
    """Admin for trip capacities."""

    list_display = ["trip", "total_weight", "used_weight", "available_weight", "unit", "is_full"]
    list_filter = ["unit", "created_at"]
    search_fields = ["trip__from_location", "trip__to_location"]
    readonly_fields = ["id", "available_weight", "is_full", "created_at", "updated_at"]

    def available_weight(self, obj):
        return obj.available_weight
    available_weight.short_description = _("Available Weight")

    def is_full(self, obj):
        return obj.is_full
    is_full.boolean = True
    is_full.short_description = _("Is Full")

