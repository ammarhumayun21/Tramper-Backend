"""
URL configuration for payments app.
"""

from django.urls import path
from .views import (
    PaymentListView,
    ReleaseEscrowView,
    PaymentCallbackView,
    WalletView,
    WalletTransactionsView,
    WithdrawView,
    ConfirmDeliveryView,
)

app_name = "payments"

urlpatterns = [
    # Payment endpoints
    path("", PaymentListView.as_view(), name="payment-list"),
    path("callback/", PaymentCallbackView.as_view(), name="payment-callback"),
    # path(
    #     "<uuid:shipment_id>/release/",
    #     ReleaseEscrowView.as_view(),
    #     name="release-escrow",
    # ),
    path(
        "<uuid:shipment_id>/confirm-delivery/",
        ConfirmDeliveryView.as_view(),
        name="confirm-delivery",
    ),
    # Wallet endpoints
    path("wallet/", WalletView.as_view(), name="wallet"),
    path(
        "wallet/transactions/",
        WalletTransactionsView.as_view(),
        name="wallet-transactions",
    ),
    path(
        "wallet/withdraw/",
        WithdrawView.as_view(),
        name="wallet-withdraw",
    ),
]
