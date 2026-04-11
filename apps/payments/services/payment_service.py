"""
Payment service for Tramper.
Orchestrates payment flow: intent creation, confirmation, and escrow release.
Handles commission calculations and wallet management.
"""

import uuid
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.payments.models import Payment, Wallet, WalletTransaction
from apps.payments.services.ziina import ZiinaService, ZiinaAPIError

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for payment orchestration."""

    def __init__(self):
        self.ziina = ZiinaService()

    def _get_payer_commission_rate(self):
        """Get payer commission rate as a Decimal (e.g., 0.10 for 10%)."""
        rate = getattr(settings, "COMMISSION_FROM_PAYER", 10)
        return Decimal(str(rate)) / Decimal("100")

    def _get_receiver_commission_rate(self):
        """Get receiver commission rate as a Decimal (e.g., 0.05 for 5%)."""
        rate = getattr(settings, "COMMISSION_FROM_RECEIVER", 5)
        return Decimal(str(rate)) / Decimal("100")

    @transaction.atomic
    def initiate_payment(self, shipment):
        """
        Initiate a payment for a shipment.
        Creates a Payment record and calls Ziina to create a payment intent.
        Adds payer commission to the reward amount for the total charge.

        Args:
            shipment: The Shipment instance (must be in 'accepted' status).

        Returns:
            Payment: The created Payment instance.

        Raises:
            ValueError: If shipment is not in 'accepted' status.
            ZiinaAPIError: If Ziina API call fails.
        """
        if shipment.status != "accepted":
            raise ValueError(
                f"Cannot initiate payment for shipment in '{shipment.status}' status. "
                "Shipment must be in 'accepted' status."
            )

        # Check if a completed payment already exists (prevent duplicate payment cycles)
        if Payment.objects.filter(
            shipment=shipment,
            status=Payment.Status.COMPLETED,
        ).exists():
            raise ValueError(
                f"A completed payment already exists for shipment {shipment.id}. "
                "Cannot create a duplicate payment."
            )

        # Check if a pending payment already exists for this shipment
        existing_payment = Payment.objects.filter(
            shipment=shipment,
            status=Payment.Status.PENDING,
        ).first()

        if existing_payment:
            logger.info(
                "Payment already exists for shipment %s: %s",
                shipment.id,
                existing_payment.id,
            )
            return existing_payment

        # Calculate commission
        reward = shipment.reward
        payer_commission_rate = self._get_payer_commission_rate()
        commission_amount = (reward * payer_commission_rate).quantize(Decimal("0.01"))
        total_charged = reward + commission_amount

        # Amount in smallest units (fils for AED: 1 AED = 100 fils)
        currency = getattr(settings, "ZIINA_CURRENCY", "AED")
        amount_in_fils = int(total_charged * 100)

        # Create Payment record first
        payment = Payment.objects.create(
            user=shipment.sender,
            shipment=shipment,
            amount=reward,
            total_charged=total_charged,
            commission_amount=commission_amount,
            currency=currency,
            status=Payment.Status.PENDING,
        )

        try:
            # Call Ziina to create payment intent
            ziina_response = self.ziina.create_payment_intent(
                amount=amount_in_fils,
                currency_code=currency,
            )

            # Save Ziina response data
            payment.ziina_payment_intent_id = ziina_response.get("id")
            payment.ziina_redirect_url = ziina_response.get("redirect_url")
            payment.save(update_fields=[
                "ziina_payment_intent_id",
                "ziina_redirect_url",
                "updated_at",
            ])

            # Now build redirect URLs with the real payment_intent_id and shipment_id
            payment_intent_id = payment.ziina_payment_intent_id or ""
            success_url = self._build_redirect_url(
                getattr(settings, "ZIINA_SUCCESS_URL", ""),
                payment_intent_id,
                str(shipment.id),
            )
            cancel_url = self._build_redirect_url(
                getattr(settings, "ZIINA_CANCLE_URL", ""),
                payment_intent_id,
                str(shipment.id),
            )
            failure_url = self._build_redirect_url(
                getattr(settings, "ZIINA_FALIURE_URL", ""),
                payment_intent_id,
                str(shipment.id),
            )

            # Update the payment intent with the correct redirect URLs
            # Since Ziina may have already been called, we update via API if needed
            # For now, the URLs are built from env templates with placeholders
            # Ziina replaces {PAYMENT_INTENT_ID} automatically in their system

            # Update shipment status to payment_pending
            shipment.status = "payment_pending"
            shipment.save(update_fields=["status", "updated_at"])

            logger.info(
                "Payment initiated for shipment %s: payment=%s, intent=%s, "
                "reward=%s, commission=%s, total_charged=%s",
                shipment.id,
                payment.id,
                payment.ziina_payment_intent_id,
                reward,
                commission_amount,
                total_charged,
            )

            return payment

        except ZiinaAPIError as e:
            # Mark payment as failed if Ziina call fails
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            logger.error(
                "Failed to initiate payment for shipment %s: %s",
                shipment.id,
                str(e),
            )
            raise

    def _build_redirect_url(self, url_template, payment_intent_id, shipment_id):
        """
        Build a redirect URL from the env template.
        Replaces {PAYMENT_INTENT_ID} placeholder and appends shipment_id.
        """
        if not url_template:
            return ""
        url = url_template.replace("{PAYMENT_INTENT_ID}", payment_intent_id)
        # Append shipment_id as query parameter
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}shipment_id={shipment_id}"
        return url

    @transaction.atomic
    def confirm_payment(self, payment, force_status=None):
        """
        Confirm a payment by checking its status with Ziina, or by using forced status.

        Args:
            payment: The Payment instance to confirm.
            force_status: Optional string to force the status (e.g. 'completed', 'failed', 'cancelled').

        Returns:
            Payment: The updated Payment instance.

        Raises:
            ZiinaAPIError: If Ziina API call fails.
        """
        if payment.status != Payment.Status.PENDING:
            logger.info(
                "Payment %s is already in '%s' status, skipping confirmation.",
                payment.id,
                payment.status,
            )
            return payment

        # Check status with Ziina unless forced
        if force_status:
            ziina_status = force_status.lower()
        else:
            if not payment.ziina_payment_intent_id:
                logger.error(
                    "Payment %s has no Ziina payment intent ID.",
                    payment.id,
                )
                raise ValueError("Payment has no Ziina payment intent ID.")

            ziina_response = self.ziina.get_payment_status(payment.ziina_payment_intent_id)
            ziina_status = ziina_response.get("status", "").lower()

        if ziina_status == "completed":
            payment.status = Payment.Status.COMPLETED
            payment.save(update_fields=["status", "updated_at"])

            # Record debit transaction but do NOT deduct wallet balance
            # The payment was made via Ziina, not from wallet
            self._record_payment_transaction(payment)

            # Update shipment status
            shipment = payment.shipment
            shipment.status = "payment_completed"
            shipment.save(update_fields=["status", "updated_at"])

            logger.info(
                "Payment %s confirmed as completed for shipment %s.",
                payment.id,
                shipment.id,
            )

        elif ziina_status == "cancelled":
            payment.status = Payment.Status.CANCELLED
            payment.save(update_fields=["status", "updated_at"])

            # Update shipment status to payment_cancelled
            shipment = payment.shipment
            shipment.status = "payment_cancelled"
            shipment.save(update_fields=["status", "updated_at"])

            logger.info(
                "Payment %s cancelled for shipment %s.",
                payment.id,
                shipment.id,
            )

        elif ziina_status == "failed":
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])

            # Revert shipment to accepted so they can retry payment
            shipment = payment.shipment
            shipment.status = "accepted"
            shipment.save(update_fields=["status", "updated_at"])

            logger.warning(
                "Payment %s failed for shipment %s. Shipment reverted to accepted.",
                payment.id,
                payment.shipment_id,
            )

        else:
            logger.info(
                "Payment %s still pending (Ziina status: %s).",
                payment.id,
                ziina_status,
            )

        return payment

    @transaction.atomic
    def credit_receiver_wallet(self, shipment):
        """
        Credit the receiver's (traveler/courier) wallet after delivery confirmation.
        The amount credited is the original reward (receiver sees the real amount).
        Commission will be deducted on withdrawal.

        Args:
            shipment: The Shipment instance (must have a completed payment).

        Returns:
            WalletTransaction: The credit transaction.

        Raises:
            ValueError: If no completed payment or no traveler.
        """
        # Get the completed payment for this shipment
        payment = Payment.objects.filter(
            shipment=shipment,
            status=Payment.Status.COMPLETED,
        ).first()

        if not payment:
            raise ValueError("No completed payment found for this shipment.")

        if not shipment.traveler:
            raise ValueError("Shipment has no assigned traveler/courier.")

        # Check if already credited to prevent duplicate wallet additions
        if WalletTransaction.objects.filter(
            wallet__user=shipment.traveler,
            reference=payment,
            type=WalletTransaction.TransactionType.CREDIT
        ).exists():
            raise ValueError("Payment has already been credited to your wallet.")

        # Update shipment status to delivered if not already
        if shipment.status not in ["delivered"]:
            shipment.status = "delivered"
            shipment.save(update_fields=["status", "updated_at"])

        # Credit the full reward amount to receiver's wallet
        # Commission will be deducted on withdrawal
        wallet_transaction = self._credit_wallet(
            user=shipment.traveler,
            amount=payment.amount,
            payment=payment,
            description=f"Payment received for shipment {shipment.name} ({shipment.id})",
        )

        logger.info(
            "Credited %s %s to courier %s wallet for shipment %s.",
            payment.amount,
            payment.currency,
            shipment.traveler.id,
            shipment.id,
        )

        return wallet_transaction

    @transaction.atomic
    def withdraw_funds(self, user, amount):
        """
        Withdraw funds from user's wallet via Ziina transfer.
        Deducts receiver commission and transfers the net amount.

        Args:
            user: The User instance requesting withdrawal.
            amount: The amount to withdraw from wallet.

        Returns:
            dict: Withdrawal details including net amount after commission.

        Raises:
            ValueError: If insufficient balance, no ziina_username set in settings, etc.
        """
        # Read ziina username from UserSettings
        ziina_username = None
        try:
            ziina_username = user.settings.ziina_username
        except Exception:
            pass

        if not ziina_username:
            raise ValueError(
                "You must set your Ziina username in Settings before withdrawing."
            )

        wallet = self._get_or_create_wallet(user)

        if wallet.balance < amount:
            raise ValueError(
                f"Insufficient wallet balance. Available: {wallet.balance}, Requested: {amount}"
            )

        # Calculate receiver commission
        receiver_commission_rate = self._get_receiver_commission_rate()
        commission = (amount * receiver_commission_rate).quantize(Decimal("0.01"))
        net_amount = amount - commission

        if net_amount <= 0:
            raise ValueError("Withdrawal amount too small after commission deduction.")

        currency = getattr(settings, "ZIINA_CURRENCY", "AED")
        amount_in_fils = int(net_amount * 100)
        operation_id = uuid.uuid4()

        # Call Ziina Transfer to send funds to user
        try:
            self.ziina.transfer_to_user(
                to_ziinames=ziina_username,
                amount=amount_in_fils,
                currency_code=currency,
                operation_id=operation_id,
            )
        except ZiinaAPIError as e:
            logger.error(
                "Failed to transfer funds to user %s: %s",
                user.id,
                str(e),
            )
            raise

        # Deduct from wallet
        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])

        # Record debit transaction
        debit_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            type=WalletTransaction.TransactionType.DEBIT,
            description=f"Withdrawal of {net_amount} {currency} (commission: {commission} {currency})",
        )

        logger.info(
            "Withdrawal processed for user %s: amount=%s, commission=%s, net=%s, ziina_username=%s",
            user.id,
            amount,
            commission,
            net_amount,
            ziina_username,
        )

        return {
            "transaction_id": str(debit_transaction.id),
            "amount": str(amount),
            "commission": str(commission),
            "net_amount": str(net_amount),
            "new_balance": str(wallet.balance),
        }

    @transaction.atomic
    def release_escrow(self, shipment, to_ziiname=None):
        """
        Release escrow payment to the courier after delivery.
        Credits the courier's wallet (commission deducted on withdrawal).

        Args:
            shipment: The Shipment instance (must be in 'delivered' status).
            to_ziiname: Ziina username of the courier (optional, for direct transfer).

        Returns:
            WalletTransaction: The credit transaction for the courier.

        Raises:
            ValueError: If shipment is not in 'delivered' status.
            ZiinaAPIError: If Ziina transfer fails.
        """
        if shipment.status != "delivered":
            raise ValueError(
                f"Cannot release escrow for shipment in '{shipment.status}' status. "
                "Shipment must be in 'delivered' status."
            )

        # Get the completed payment for this shipment
        payment = Payment.objects.filter(
            shipment=shipment,
            status=Payment.Status.COMPLETED,
        ).first()

        if not payment:
            raise ValueError("No completed payment found for this shipment.")

        if not shipment.traveler:
            raise ValueError("Shipment has no assigned traveler/courier.")

        # Check if already credited to prevent duplicate wallet additions
        if WalletTransaction.objects.filter(
            wallet__user=shipment.traveler,
            reference=payment,
            type=WalletTransaction.TransactionType.CREDIT
        ).exists():
            raise ValueError("Payment has already been credited to the courier's wallet.")

        # Credit courier's wallet with the full reward amount
        # Commission will be deducted when they withdraw
        wallet_transaction = self._credit_wallet(
            user=shipment.traveler,
            amount=payment.amount,
            payment=payment,
            description=f"Escrow release for shipment {shipment.name} ({shipment.id})",
        )

        logger.info(
            "Escrow released for shipment %s: credited %s %s to courier %s.",
            shipment.id,
            payment.amount,
            payment.currency,
            shipment.traveler.id,
        )

        return wallet_transaction

    def _get_or_create_wallet(self, user):
        """Get or create a wallet for a user."""
        wallet, created = Wallet.objects.get_or_create(user=user)
        if created:
            logger.info("Created wallet for user %s.", user.id)
        return wallet

    def _record_payment_transaction(self, payment):
        """
        Record a debit transaction for a payment WITHOUT deducting wallet balance.
        This is for tracking purposes only — the actual payment was via Ziina.
        """
        wallet = self._get_or_create_wallet(payment.user)

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=payment.total_charged,
            type=WalletTransaction.TransactionType.DEBIT,
            reference=payment,
            description=(
                f"Payment for shipment {payment.shipment.name} ({payment.shipment_id}) "
                f"— Paid via Ziina (reward: {payment.amount}, commission: {payment.commission_amount})"
            ),
        )

        logger.info(
            "Recorded payment transaction for user %s: %s (no wallet deduction)",
            payment.user.id,
            payment.total_charged,
        )

    def _credit_wallet(self, user, amount, payment, description=""):
        """Credit a user's wallet."""
        wallet = self._get_or_create_wallet(user)
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        tx = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            type=WalletTransaction.TransactionType.CREDIT,
            reference=payment,
            description=description,
        )

        logger.info(
            "Credited %s to wallet of user %s. New balance: %s",
            amount,
            user.id,
            wallet.balance,
        )

        return tx


# Module-level singleton
payment_service = PaymentService()
