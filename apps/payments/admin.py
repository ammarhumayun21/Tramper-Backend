"""
Admin configuration for payments app.
"""

from django.contrib import admin
from .models import Payment, Wallet, WalletTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "shipment",
        "amount",
        "currency",
        "status",
        "created_at",
    ]
    list_filter = ["status", "currency", "created_at"]
    search_fields = [
        "user__full_name",
        "user__email",
        "shipment__name",
        "ziina_payment_intent_id",
    ]
    readonly_fields = [
        "id",
        "ziina_payment_intent_id",
        "ziina_redirect_url",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user", "shipment"]


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "balance", "updated_at"]
    search_fields = ["user__full_name", "user__email"]
    readonly_fields = ["id", "updated_at"]
    raw_id_fields = ["user"]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "wallet", "amount", "type", "reference", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["wallet__user__full_name", "wallet__user__email", "description"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["wallet", "reference"]
