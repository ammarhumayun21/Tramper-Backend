"""
Verification center serializers for Tramper.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import VerificationRequest
from apps.users.serializers import UserSerializer


class VerificationSubmitSerializer(serializers.Serializer):
    """Serializer for user submitting verification documents (form-data)."""

    id_card_number = serializers.CharField(
        max_length=50,
        required=True,
        help_text=_("Number written on the ID card."),
    )

    id_card_front = serializers.ImageField(
        required=True,
        help_text=_("Front side of ID card image."),
    )

    id_card_back = serializers.ImageField(
        required=True,
        help_text=_("Back side of ID card image."),
    )

    selfie_with_id = serializers.ImageField(
        required=True,
        help_text=_("Selfie photo holding ID card."),
    )

    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text=_("Phone number for verification (optional)."),
    )


class PhoneVerifySerializer(serializers.Serializer):
    """Serializer for submitting/verifying phone number."""

    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text=_("Phone number to verify."),
    )


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for verification request details."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = VerificationRequest
        fields = [
            "id",
            "user",
            "id_card_number",
            "id_card_front_url",
            "id_card_back_url",
            "selfie_with_id_url",
            "phone_number",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class VerificationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing verification requests (admin)."""

    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = VerificationRequest
        fields = [
            "id",
            "user_id",
            "user_email",
            "user_full_name",
            "id_card_number",
            "phone_number",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class VerificationReviewSerializer(serializers.Serializer):
    """Serializer for admin reviewing a verification request."""

    status = serializers.ChoiceField(
        choices=["approved", "rejected"],
        help_text=_("Set verification status to approved or rejected."),
    )

    admin_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("Optional notes from admin."),
    )
