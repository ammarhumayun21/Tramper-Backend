"""
Core admin configuration.
"""

from django.contrib import admin
from .models import Location, Airline, Country, City


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin for Country model."""

    list_display = ["name", "alpha_2", "alpha_3", "region", "flag_emoji", "has_airports"]
    list_filter = ["region", "sub_region", "has_airports"]
    search_fields = ["name", "alpha_2", "alpha_3"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """Admin for City model."""

    list_display = ["name", "country", "latitude", "longitude", "created_at"]
    list_filter = ["country__region"]
    search_fields = ["name", "country__name"]
    ordering = ["country__name", "name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["country"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin for Location model."""

    list_display = ["city", "country", "airport_name", "iata_code", "created_at"]
    list_filter = ["country"]
    search_fields = ["city", "country", "airport_name", "iata_code"]
    ordering = ["country", "city"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["city_ref"]


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    """Admin for Airline model."""

    list_display = ["name", "iata_code", "country", "created_at"]
    list_filter = ["country"]
    search_fields = ["name", "iata_code", "country"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["country_ref"]
