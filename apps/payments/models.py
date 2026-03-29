"""
Payment models for Tramper.
Handles escrow-based payments via Ziina.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Payment(models.Model):
    """
    Payment model representing a Ziina payment intent.
    Tracks the payment lifecycle from creation through completion.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("payer"),
        help_text=_("The user who makes the payment (sender of shipment)."),
    )

    shipment = models.ForeignKey(
        "shipments.Shipment",
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("shipment"),
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("amount"),
        help_text=_("Original reward amount (what the receiver sees)."),
    )

    total_charged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("total charged"),
        help_text=_("Total amount charged to payer (reward + payer commission)."),
    )

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("commission amount"),
        help_text=_("Commission amount collected from the payer."),
    )

    currency = models.CharField(
        max_length=10,
        default="AED",
        verbose_name=_("currency"),
    )

    ziina_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Ziina payment intent ID"),
    )

    ziina_redirect_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("Ziina redirect URL"),
        help_text=_("URL to redirect the user to for payment."),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("status"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} ({self.status})"


class Wallet(models.Model):
    """
    Wallet model for tracking user balances.
    Each user has one wallet.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        verbose_name=_("user"),
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("balance"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("wallet")
        verbose_name_plural = _("wallets")

    def __str__(self):
        return f"Wallet for {self.user} - {self.balance}"


class WalletTransaction(models.Model):
    """
    Wallet transaction model.
    Records all debits and credits to a wallet.
    """

    class TransactionType(models.TextChoices):
        DEBIT = "debit", _("Debit")
        CREDIT = "credit", _("Credit")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("wallet"),
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("amount"),
    )

    type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        verbose_name=_("type"),
    )

    reference = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_transactions",
        verbose_name=_("reference payment"),
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("description"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("wallet transaction")
        verbose_name_plural = _("wallet transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} {self.amount} - {self.wallet.user}"
