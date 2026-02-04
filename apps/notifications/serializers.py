"""
Notification serializers for Tramper.
"""

from rest_framework import serializers
from .models import Notification


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
