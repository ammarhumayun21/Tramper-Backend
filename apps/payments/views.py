"""
Payment views for Tramper.
Handles payment listing, escrow release, callbacks, wallet operations, and withdrawals.
"""

import logging
import secrets
from decimal import Decimal

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Payment, Wallet, WalletTransaction
from .serializers import (
    PaymentSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
    ReleaseEscrowSerializer,
    WithdrawSerializer,
)
from .services.payment_service import payment_service
from .services.ziina import ZiinaAPIError
from core.api import success_response, error_response

logger = logging.getLogger(__name__)


class PaymentListView(ListAPIView):
    """
    List current user's payments.
    GET /api/v1/payments/
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        return Payment.objects.filter(user=self.request.user).select_related(
            "user", "shipment"
        )

    @extend_schema(
        tags=["Payments"],
        summary="List user payments",
        description="Get all payments for the currently authenticated user.",
        responses={
            200: OpenApiResponse(
                response=PaymentSerializer(many=True),
                description="List of payments",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ReleaseEscrowView(APIView):
    """
    Release escrow payment to courier after shipment delivery.
    POST /api/v1/payments/{shipment_id}/release/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Release escrow payment",
        description=(
            "Release the escrow payment to the courier after shipment is delivered. "
            "Only the shipment sender or an admin can release."
        ),
        request=ReleaseEscrowSerializer,
        responses={
            200: OpenApiResponse(description="Escrow released successfully"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def post(self, request, shipment_id):
        from apps.shipments.models import Shipment

        try:
            shipment = Shipment.objects.select_related("sender", "traveler").get(
                pk=shipment_id
            )
        except Shipment.DoesNotExist:
            return error_response(
                "Shipment not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Only sender or admin can release escrow
        if shipment.sender != request.user and not request.user.is_staff:
            return error_response(
                "Only the shipment sender or an admin can release escrow.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReleaseEscrowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            wallet_transaction = payment_service.release_escrow(
                shipment=shipment,
            )
            return success_response({
                "message": "Escrow released successfully.",
                "transaction_id": str(wallet_transaction.id),
                "amount": str(wallet_transaction.amount),
                "courier_id": str(shipment.traveler.id),
            })
        except ValueError as e:
            return error_response(
                str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except ZiinaAPIError as e:
            logger.error("Escrow release failed: %s", str(e))
            return error_response(
                "Failed to release escrow. Please try again.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class PaymentCallbackView(APIView):
    """
    Payment callback/webhook endpoint.
    POST /api/v1/payments/callback/
    Called after payment is completed (e.g., by redirect or webhook).
    """

    permission_classes = []  # Allow unauthenticated (webhook)

    @extend_schema(
        tags=["Payments"],
        summary="Payment callback",
        description=(
            "Callback endpoint for Ziina payment completion. "
            "Confirms the payment and updates shipment status. "
            "Accepts status values: 'completed', 'failed', 'cancelled'."
        ),
        responses={
            200: OpenApiResponse(description="Payment confirmed"),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Payment not found"),
        },
    )
    def post(self, request):
        payment_intent_id = request.data.get("payment_intent_id")
        shipment_id = request.data.get("shipment_id")
        status_override = request.data.get("status")

        if not payment_intent_id and not shipment_id:
            return error_response(
                "payment_intent_id or shipment_id is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if payment_intent_id:
                payment = Payment.objects.select_related("shipment", "user").get(
                    ziina_payment_intent_id=payment_intent_id
                )
            else:
                payment = Payment.objects.select_related("shipment", "user").filter(
                    shipment_id=shipment_id
                ).order_by("-created_at").first()
                if not payment:
                    raise Payment.DoesNotExist
        except Payment.DoesNotExist:
            return error_response(
                "Payment not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            updated_payment = payment_service.confirm_payment(
                payment, force_status=status_override
            )
            return success_response({
                "message": "Payment status updated.",
                "payment_id": str(updated_payment.id),
                "status": updated_payment.status,
                "shipment_id": str(updated_payment.shipment_id),
            })
        except (ValueError, ZiinaAPIError) as e:
            logger.error("Payment confirmation failed: %s", str(e))
            return error_response(
                f"Payment confirmation failed: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class WalletView(APIView):
    """
    Get current user's wallet.
    GET /api/v1/payments/wallet/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Get wallet",
        description="Get the current user's wallet balance.",
        responses={
            200: OpenApiResponse(
                response=WalletSerializer,
                description="Wallet details",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return success_response(serializer.data)


class WalletTransactionsView(ListAPIView):
    """
    List wallet transactions for the current user.
    GET /api/v1/payments/wallet/transactions/
    """

    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return WalletTransaction.objects.none()
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return WalletTransaction.objects.filter(wallet=wallet).select_related(
            "reference"
        )

    @extend_schema(
        tags=["Payments"],
        summary="List wallet transactions",
        description="Get all wallet transactions for the currently authenticated user.",
        responses={
            200: OpenApiResponse(
                response=WalletTransactionSerializer(many=True),
                description="List of wallet transactions",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class WithdrawView(APIView):
    """
    Withdraw funds from wallet via Ziina transfer.
    POST /api/v1/payments/wallet/withdraw/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Withdraw funds",
        description=(
            "Withdraw funds from wallet. Transfers net amount (after receiver commission) "
            "to the user's Ziina account. The user's ziina_username must be set in their Settings."
        ),
        request=WithdrawSerializer,
        responses={
            200: OpenApiResponse(description="Withdrawal successful"),
            400: OpenApiResponse(description="Bad request"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = Decimal(str(serializer.validated_data["amount"]))

        try:
            result = payment_service.withdraw_funds(
                user=request.user,
                amount=amount,
            )
            return success_response({
                "message": "Withdrawal completed successfully.",
                **result,
            })
        except ValueError as e:
            return error_response(
                str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except ZiinaAPIError as e:
            logger.error("Withdrawal failed for user %s: %s", request.user.id, str(e))
            return error_response(
                "Withdrawal failed. Please try again.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class ConfirmDeliveryView(APIView):
    """
    Confirm shipment delivery and credit receiver's wallet.
    POST /api/v1/payments/{shipment_id}/confirm-delivery/
    Called when the payer scans the QR code to confirm delivery.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Payments"],
        summary="Confirm delivery and credit wallet",
        description=(
            "Confirm that a shipment has been delivered. Credits the courier's wallet "
            "with the reward amount. Only the shipment sender or admin can confirm."
        ),
        responses={
            200: OpenApiResponse(description="Delivery confirmed, wallet credited"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def post(self, request, shipment_id):
        from apps.shipments.models import Shipment
        from apps.requests.models import Request as ShipmentRequest

        try:
            shipment = Shipment.objects.select_related("sender", "traveler").get(
                pk=shipment_id
            )
        except Shipment.DoesNotExist:
            return error_response(
                "Shipment not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Only sender or admin can confirm delivery
        if shipment.sender != request.user and not request.user.is_staff:
            return error_response(
                "Only the shipment sender or an admin can confirm delivery.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Validate QR token
        token = request.data.get("token") or request.query_params.get("token")
        if not token:
            return error_response(
                "QR code token is required to confirm delivery.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        accepted_request = ShipmentRequest.objects.filter(
            shipment=shipment, status="accepted"
        ).first()

        if not accepted_request or not accepted_request.qr_token:
            return error_response(
                "No active delivery QR code found for this shipment.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not secrets.compare_digest(token, accepted_request.qr_token):
            return error_response(
                "Invalid QR code token.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Verify the payment was completed
        completed_payment = Payment.objects.filter(
            shipment=shipment,
            status=Payment.Status.COMPLETED,
        ).first()

        if not completed_payment:
            return error_response(
                "No completed payment found for this shipment. Cannot confirm delivery.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            wallet_transaction = payment_service.credit_receiver_wallet(shipment)

            # Clean up QR code after successful confirmation
            if accepted_request.qr_code_url:
                from core.storage import s3_storage
                s3_storage.delete_image(accepted_request.qr_code_url)
            accepted_request.qr_code_url = None
            accepted_request.qr_token = None
            accepted_request.save(update_fields=["qr_code_url", "qr_token", "updated_at"])

            return success_response({
                "message": "Delivery confirmed. Payment credited to courier's wallet.",
                "transaction_id": str(wallet_transaction.id),
                "amount": str(wallet_transaction.amount),
                "courier_id": str(shipment.traveler.id),
            })
        except ValueError as e:
            return error_response(
                str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
