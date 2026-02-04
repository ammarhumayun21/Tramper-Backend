"""
Admin configuration for requests app.
"""

from django.contrib import admin
from .models import Request, CounterOffer


class CounterOfferInline(admin.TabularInline):
    """Inline for counter offers."""
    
    model = CounterOffer
    extra = 0
    readonly_fields = ("id", "created_at")
    fields = ("id", "sender", "receiver", "price", "message", "created_at")


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Admin for Request model."""
    
    list_display = (
        "id",
        "sender",
        "receiver",
        "shipment",
        "trip",
        "offered_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "sender__email",
        "sender__first_name",
        "receiver__email",
        "receiver__first_name",
        "shipment__title",
        "trip__title",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("sender", "receiver", "shipment", "trip")
    inlines = [CounterOfferInline]
    ordering = ("-created_at",)


@admin.register(CounterOffer)
class CounterOfferAdmin(admin.ModelAdmin):
    """Admin for CounterOffer model."""
    
    list_display = (
        "id",
        "request",
        "sender",
        "receiver",
        "price",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "request__id",
        "sender__email",
        "sender__first_name",
        "receiver__email",
        "receiver__first_name",
    )
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("request", "sender", "receiver")
    ordering = ("-created_at",)
