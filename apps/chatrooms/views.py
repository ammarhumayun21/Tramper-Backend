"""
Chatroom views for Tramper.
REST endpoints for admin chatroom listing, file message uploads, and chatroom management.
"""

import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
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


class ChatRoomListView(ListAPIView):
    """
    List all chatrooms. Admin only.
    GET /api/v1/chatrooms/
    """

    serializer_class = ChatRoomListSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ChatRoom.objects.none()

        user = self.request.user
        last_msg_subquery = (
            Message.objects.filter(chatroom=OuterRef("pk"), is_deleted=False)
            .order_by("-created_at")
            .values("pk")[:1]
        )
        queryset = (
            ChatRoom.objects.filter(Q(sender=user) | Q(receiver=user))
            .select_related("sender", "receiver", "request")
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
        return queryset

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        return ctx

    @extend_schema(
        tags=["Chatrooms"],
        summary="List all chatrooms (admin)",
        description="Returns all chatrooms. Admin only.",
        responses={
            200: OpenApiResponse(
                response=ChatRoomListSerializer(many=True),
                description="List of chatrooms",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Attach prefetched last messages to serializer objects
        if hasattr(response, "data") and "data" in response.data:
            pass  # Handled by serializer's get_last_message
        return response


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
