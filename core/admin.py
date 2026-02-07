"""
Core admin configuration.
"""

from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin for Location model."""
    
    list_display = ["city", "country", "airport_name", "iata_code", "created_at"]
    list_filter = ["country"]
    search_fields = ["city", "country", "airport_name", "iata_code"]
    ordering = ["country", "city"]
    readonly_fields = ["id", "created_at", "updated_at"]
