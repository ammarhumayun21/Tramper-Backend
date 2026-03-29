"""
Payment serializers for Tramper.
"""

from rest_framework import serializers

from .models import Payment, Wallet, WalletTransaction


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""

    user_name = serializers.SerializerMethodField()
    shipment_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "user",
            "user_name",
            "shipment",
            "shipment_name",
            "amount",
            "total_charged",
            "commission_amount",
            "currency",
            "ziina_payment_intent_id",
            "ziina_redirect_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.username if obj.user else None

    def get_shipment_name(self, obj):
        return obj.shipment.name if obj.shipment else None


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model."""

    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            "id",
            "user",
            "user_name",
            "balance",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.username if obj.user else None


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for WalletTransaction model."""

    reference_id = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "wallet",
            "amount",
            "type",
            "reference",
            "reference_id",
            "description",
            "created_at",
        ]
        read_only_fields = fields

    def get_reference_id(self, obj):
        return str(obj.reference_id) if obj.reference_id else None


class ReleaseEscrowSerializer(serializers.Serializer):
    """Serializer for escrow release endpoint."""

    pass


class WithdrawSerializer(serializers.Serializer):
    """Serializer for wallet withdrawal endpoint."""

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        help_text="Amount to withdraw from wallet.",
    )
