"""
Admin configuration for shipments.
"""

from django.contrib import admin
from .models import Shipment, ShipmentItem, Dimension, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "icon", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):
    list_display = ["id", "height", "width", "length", "unit"]


class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 1


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sender", "traveler", "status", "travel_date", "reward", "created_at"]
    list_filter = ["status", "travel_date", "created_at"]
    search_fields = ["name", "from_location", "to_location", "sender__email", "traveler__email"]
    inlines = [ShipmentItemInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ShipmentItem)
class ShipmentItemAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "shipment", "category", "quantity", "single_item_price", "single_item_weight"]
    list_filter = ["category", "weight_unit"]
    search_fields = ["name", "shipment__name"]
