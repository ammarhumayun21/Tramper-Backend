"""
Notification serializers for Tramper.
"""

from rest_framework import serializers
from .models import Notification, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications."""

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "category",
            "is_read",
            "request_id",
            "shipment_id",
            "trip_id",
            "timestamp",
        ]
        read_only_fields = fields


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""
    
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of notification IDs to mark as read. If empty, marks all as read.",
    )


class DeviceTokenRegisterSerializer(serializers.Serializer):
    """Serializer for registering an FCM device token."""

    token = serializers.CharField(
        max_length=500,
        help_text="FCM registration token from the client device.",
    )
    device_type = serializers.ChoiceField(
        choices=["ios", "android", "web"],
        help_text="Platform type of the device.",
    )


class DeviceTokenDeleteSerializer(serializers.Serializer):
    """Serializer for deleting an FCM device token (logout)."""

    token = serializers.CharField(
        max_length=500,
        help_text="FCM registration token to remove.",
    )


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Read-only serializer for DeviceToken model."""

    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "token",
            "device_type",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
