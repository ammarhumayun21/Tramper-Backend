"""
Chatroom serializers for Tramper.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from .models import ChatRoom, Message
from core.storage import s3_storage


class ChatLocationSerializer(serializers.Serializer):
    """Lightweight location serializer for chatroom context."""

    city = serializers.CharField(read_only=True)
    country = serializers.CharField(read_only=True)
    iata_code = serializers.CharField(read_only=True)


class ChatShipmentSerializer(serializers.Serializer):
    """Lightweight shipment serializer for chatroom context."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    from_location = ChatLocationSerializer(read_only=True)
    to_location = ChatLocationSerializer(read_only=True)


class ChatTripSerializer(serializers.Serializer):
    """Lightweight trip serializer for chatroom context."""

    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    departure_date = serializers.DateField(read_only=True)
    from_location = ChatLocationSerializer(read_only=True)
    to_location = ChatLocationSerializer(read_only=True)


class ChatRequestSerializer(serializers.Serializer):
    """Lightweight request serializer for chatroom context."""

    id = serializers.UUIDField(read_only=True)
    status = serializers.CharField(read_only=True)
    offered_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    shipment = ChatShipmentSerializer(read_only=True)
    trip = ChatTripSerializer(read_only=True)


class ChatUserSerializer(serializers.Serializer):
    """Lightweight user serializer for chatroom responses."""

    id = serializers.UUIDField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    profile_image_url = serializers.URLField(read_only=True, allow_null=True)
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)


class MessageSerializer(serializers.ModelSerializer):
    """Full message serializer."""

    sender = ChatUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "chatroom",
            "sender",
            "message_type",
            "text",
            "file",
            "created_at",
            "is_deleted",
            "is_seen",
        ]
        read_only_fields = fields


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a new message."""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    message_type = serializers.ChoiceField(choices=Message.MESSAGE_TYPE_CHOICES, default="text")
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)

    def validate_file(self, value):
        if value and value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                _("File size must not exceed 10 MB.")
            )
        return value

    def validate(self, attrs):
        message_type = attrs.get("message_type", "text")
        text = attrs.get("text")
        file = attrs.get("file")

        if message_type == "text":
            if not text or not text.strip():
                raise serializers.ValidationError(
                    {"text": _("Text is required for text messages.")}
                )
        else:
            if not file:
                raise serializers.ValidationError(
                    {"file": _(f"A file is required for {message_type} messages.")}
                )

        return attrs

    def create(self, validated_data):
        file = validated_data.pop("file", None)
        file_url = None

        if file:
            file_url = s3_storage.upload_image(file, folder="chatrooms/files")

        return Message.objects.create(
            **validated_data,
            file=file_url,
        )


class LastMessageSerializer(serializers.ModelSerializer):
    """Minimal message serializer for chatroom list preview."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender_id", "message_type", "text", "created_at"]
        read_only_fields = fields


class ChatRoomSerializer(serializers.ModelSerializer):
    """Full chatroom serializer."""

    sender = ChatUserSerializer(read_only=True)
    receiver = ChatUserSerializer(read_only=True)
    request_id = serializers.UUIDField(source="request.id", read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "sender",
            "receiver",
            "request_id",
            "is_active",
            "created_at",
            "disabled_at",
        ]
        read_only_fields = fields


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Lightweight chatroom serializer for list view with last message preview."""

    sender = ChatUserSerializer(read_only=True)
    receiver = ChatUserSerializer(read_only=True)
    request_id = serializers.UUIDField(source="request.id", read_only=True)
    request_detail = ChatRequestSerializer(source="request", read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "sender",
            "receiver",
            "request_id",
            "request_detail",
            "is_active",
            "created_at",
            "disabled_at",
            "last_message",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        # Uses prefetched last_message annotation or fallback query
        message = getattr(obj, "_last_message", None)
        if message is None:
            message = (
                obj.messages.filter(is_deleted=False).order_by("-created_at").first()
            )
        if message:
            return LastMessageSerializer(message).data
        return None



