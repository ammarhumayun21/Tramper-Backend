"""
Chatroom views for Tramper.
REST endpoints for admin chatroom listing, file message uploads, and chatroom management.
"""

import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q, Prefetch, Subquery, OuterRef
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ChatRoom, Message
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)
from .consumers import _build_chatroom_update
from .permissions import IsChatParticipant
from .services import disable_chatroom
from core.api import success_response
from core.permissions import IsAdmin


class ChatRoomListView(APIView):
    """
    List all chatrooms with search, filter, and pagination. Admin only.
    GET /api/v1/chatrooms/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Chatrooms"],
        summary="List all chatrooms (admin)",
        description="Returns all chatrooms with search, status filter, and pagination. Admin only.",
        responses={
            200: OpenApiResponse(
                response=ChatRoomListSerializer(many=True),
                description="List of chatrooms",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 12))

        last_msg_subquery = (
            Message.objects.filter(chatroom=OuterRef("pk"), is_deleted=False)
            .order_by("-created_at")
            .values("pk")[:1]
        )
        qs = (
            ChatRoom.objects.all()
            .select_related(
                "sender",
                "receiver",
                "request",
                "request__shipment",
                "request__shipment__from_location",
                "request__shipment__to_location",
                "request__trip",
                "request__trip__from_location",
                "request__trip__to_location",
            )
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=Message.objects.filter(
                        pk__in=Subquery(last_msg_subquery)
                    ).select_related("sender"),
                    to_attr="_prefetched_last_messages",
                )
            )
            .order_by("-created_at")
        )

        if search:
            qs = qs.filter(
                Q(sender__full_name__icontains=search)
                | Q(sender__username__icontains=search)
                | Q(receiver__full_name__icontains=search)
                | Q(receiver__username__icontains=search)
            )

        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "disabled":
            qs = qs.filter(is_active=False)

        total = qs.count()
        start = (page - 1) * page_size
        chatrooms = qs[start : start + page_size]

        serializer = ChatRoomListSerializer(chatrooms, many=True)
        return success_response({
            "results": serializer.data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class SendMessageView(APIView):
    """
    Send a message to a chatroom (REST API fallback).
    POST /api/v1/chatrooms/<uuid:pk>/send/
    """

    permission_classes = [IsAuthenticated, IsChatParticipant]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk):
        try:
            chatroom = ChatRoom.objects.select_related("sender", "receiver").get(pk=pk)
            self.check_object_permissions(self.request, chatroom)
            return chatroom
        except ChatRoom.DoesNotExist:
            return None

    @extend_schema(
        tags=["Chatrooms"],
        summary="Send a message",
        description="Send a message to a chatroom via REST API. Supports text, image, video, and file types.",
        request=MessageCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=MessageSerializer, description="Message sent"
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not a participant or chatroom disabled"),
            404: OpenApiResponse(description="Chatroom not found"),
        },
    )
    def post(self, request, pk):
        chatroom = self.get_object(pk)
        if not chatroom:
            return success_response(
                {"message": "Chatroom not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not chatroom.is_active:
            return success_response(
                {"message": "This chatroom is disabled. You cannot send messages."},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(chatroom=chatroom, sender=request.user)

        # Broadcast to WebSocket group so real-time clients receive it
        message_data = MessageSerializer(message).data
        channel_layer = get_channel_layer()
        if channel_layer:
            # Convert to JSON-safe dict (UUIDs → strings) for Redis msgpack serializer
            safe_message_data = json.loads(json.dumps(message_data, default=str))
            async_to_sync(channel_layer.group_send)(
                f"chat_{chatroom.id}",
                {
                    "type": "chat.message",
                    "message": safe_message_data,
                },
            )

            # Push chatroom_update to both users' global WS groups
            for user in (chatroom.sender, chatroom.receiver):
                update = _build_chatroom_update(chatroom, user)
                safe_update = json.loads(json.dumps(update, default=str))
                async_to_sync(channel_layer.group_send)(
                    f"user_{user.id}",
                    {
                        "type": "chatroom.update",
                        "chatroom": safe_update,
                    },
                )

        return success_response(
            message_data,
            status_code=status.HTTP_201_CREATED,
        )


class DisableChatRoomView(APIView):
    """
    Disable a chatroom. Admin only.
    POST /api/v1/chatrooms/<uuid:pk>/disable/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Chatrooms"],
        summary="Disable a chatroom",
        description="Disable a chatroom so no more messages can be sent. Admin only.",
        responses={
            200: OpenApiResponse(
                response=ChatRoomSerializer, description="Chatroom disabled"
            ),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not an admin"),
            404: OpenApiResponse(description="Chatroom not found"),
        },
    )
    def post(self, request, pk):
        try:
            chatroom = ChatRoom.objects.select_related("sender", "receiver").get(pk=pk)
        except ChatRoom.DoesNotExist:
            return success_response(
                {"message": "Chatroom not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not chatroom.is_active:
            return success_response(
                {"message": "Chatroom is already disabled."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        disable_chatroom(chatroom)
        return success_response(ChatRoomSerializer(chatroom).data)


class EnableChatRoomView(APIView):
    """
    Enable a disabled chatroom. Admin only.
    POST /api/v1/chatrooms/<uuid:pk>/enable/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Chatrooms"],
        summary="Enable a chatroom",
        description="Re-enable a disabled chatroom so messages can be sent again. Admin only.",
        responses={
            200: OpenApiResponse(
                response=ChatRoomSerializer, description="Chatroom enabled"
            ),
            400: OpenApiResponse(description="Chatroom is already active"),
            404: OpenApiResponse(description="Chatroom not found"),
        },
    )
    def post(self, request, pk):
        try:
            chatroom = ChatRoom.objects.select_related("sender", "receiver").get(pk=pk)
        except ChatRoom.DoesNotExist:
            return success_response(
                {"message": "Chatroom not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if chatroom.is_active:
            return success_response(
                {"message": "Chatroom is already active."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        chatroom.is_active = True
        chatroom.disabled_at = None
        chatroom.save(update_fields=["is_active", "disabled_at"])
        return success_response(ChatRoomSerializer(chatroom).data)
