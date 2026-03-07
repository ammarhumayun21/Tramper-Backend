"""
Chatroom views for Tramper.
Handles chatroom listing, message retrieval, and message sending (API fallback).
"""

import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Q, Prefetch, Subquery, OuterRef, Count
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ChatRoom, Message
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    UnreadCountSerializer,
)
from .permissions import IsChatParticipant
from .services import disable_chatroom
from core.api import success_response
from core.permissions import IsAdmin


class ChatRoomListView(ListAPIView):
    """
    List chatrooms for the logged-in user.
    GET /api/v1/chatrooms/
    """

    serializer_class = ChatRoomListSerializer
    permission_classes = [IsAuthenticated]

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
        summary="List my chatrooms",
        description="Returns chatrooms where the current user is a participant.",
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


class ChatRoomMessagesView(ListAPIView):
    """
    List paginated messages for a chatroom.
    GET /api/v1/chatrooms/<uuid:pk>/messages/
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsChatParticipant]

    def get_chatroom(self):
        try:
            chatroom = ChatRoom.objects.select_related("sender", "receiver").get(
                pk=self.kwargs["pk"]
            )
            self.check_object_permissions(self.request, chatroom)
            return chatroom
        except ChatRoom.DoesNotExist:
            return None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Message.objects.none()

        chatroom = self.get_chatroom()
        if not chatroom:
            return Message.objects.none()

        return (
            Message.objects.filter(chatroom=chatroom, is_deleted=False)
            .select_related("sender")
            .order_by("-created_at")
        )

    @extend_schema(
        tags=["Chatrooms"],
        summary="Get chatroom messages",
        description="Returns paginated messages for a chatroom. Only participants can access.",
        responses={
            200: OpenApiResponse(
                response=MessageSerializer(many=True),
                description="Paginated messages",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not a participant"),
            404: OpenApiResponse(description="Chatroom not found"),
        },
    )
    def get(self, request, *args, **kwargs):
        chatroom = self.get_chatroom()
        if not chatroom:
            return success_response(
                {"message": "Chatroom not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return super().get(request, *args, **kwargs)


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


class UnreadCountView(APIView):
    """
    Get unread message counts for all chatrooms of the current user.
    GET /api/v1/chatrooms/unread/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Chatrooms"],
        summary="Get unread message counts",
        description="Returns chatroom_id and unread_count for all chatrooms where the current user has unseen messages.",
        responses={
            200: OpenApiResponse(
                response=UnreadCountSerializer(many=True),
                description="Unread counts per chatroom",
            ),
        },
    )
    def get(self, request):
        user = request.user
        unread_data = (
            Message.objects.filter(
                chatroom__in=ChatRoom.objects.filter(
                    Q(sender=user) | Q(receiver=user)
                ),
                is_seen=False,
                is_deleted=False,
            )
            .exclude(sender=user)
            .values("chatroom_id")
            .annotate(unread_count=Count("id"))
            .order_by()
        )

        results = [
            {"chatroom_id": item["chatroom_id"], "unread_count": item["unread_count"]}
            for item in unread_data
        ]
        return success_response(results)


class MarkMessagesSeenView(APIView):
    """
    Mark all messages in a chatroom as seen for the current user.
    POST /api/v1/chatrooms/<uuid:pk>/seen/
    """

    permission_classes = [IsAuthenticated, IsChatParticipant]

    @extend_schema(
        tags=["Chatrooms"],
        summary="Mark messages as seen",
        description="Mark all unseen messages in a chatroom as seen. Only marks messages sent by the other user.",
        responses={
            200: OpenApiResponse(description="Messages marked as seen"),
            404: OpenApiResponse(description="Chatroom not found"),
        },
    )
    def post(self, request, pk):
        try:
            chatroom = ChatRoom.objects.select_related("sender", "receiver").get(pk=pk)
            self.check_object_permissions(request, chatroom)
        except ChatRoom.DoesNotExist:
            return success_response(
                {"message": "Chatroom not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        updated = Message.objects.filter(
            chatroom=chatroom,
            is_seen=False,
            is_deleted=False,
        ).exclude(
            sender=request.user,
        ).update(is_seen=True)

        return success_response({"marked_seen": updated})
