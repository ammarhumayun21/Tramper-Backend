"""
WebSocket consumer for real-time chat messaging.
"""

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import ChatRoom, Message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for chatroom messaging.

    Connection: ws/chat/<chatroom_id>/?token=<jwt>
    - Only the two participants can connect.
    - Rejects connections from unauthenticated or unauthorized users.
    - Rejects new messages if the chatroom is disabled.
    - Saves every incoming message to the database.
    - Broadcasts messages to the chatroom group.
    """

    async def connect(self):
        self.chatroom_id = self.scope["url_route"]["kwargs"]["chatroom_id"]
        self.room_group_name = f"chat_{self.chatroom_id}"
        self.user = self.scope.get("user", AnonymousUser())

        # Reject unauthenticated users
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        # Fetch chatroom and verify participant
        self.chatroom = await self.get_chatroom()
        if self.chatroom is None:
            await self.close(code=4404)
            return

        # Allow admin/staff to monitor without being a participant
        self.is_admin = await self.check_is_staff()
        if not self.is_admin and not await self.is_participant():
            await self.close(code=4403)
            return

        if not self.is_admin and not self.chatroom.is_active:
            await self.close(code=4403)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        """Handle incoming WebSocket messages."""
        # Admin monitors are read-only
        if getattr(self, "is_admin", False):
            await self.send_json({"error": "Admin monitoring mode — sending messages is disabled."})
            return

        # Re-check chatroom is still active
        is_active = await self.check_chatroom_active()
        if not is_active:
            await self.send_json(
                {"error": "Chatroom is disabled. You cannot send messages."}
            )
            return

        message_type = content.get("message_type", "text")
        text = content.get("text", "")

        # Validate
        if message_type not in ("text", "image", "video", "file"):
            await self.send_json({"error": "Invalid message type."})
            return

        if message_type == "text" and (not text or not text.strip()):
            await self.send_json({"error": "Text is required for text messages."})
            return

        # For file-based messages via WebSocket, expect a message_id
        # referencing a message already created via the REST API.
        if message_type in ("image", "video", "file"):
            message_id = content.get("message_id")
            if message_id:
                message_data = await self.get_existing_message(message_id)
                if message_data is None:
                    await self.send_json({"error": "Message not found."})
                    return
            else:
                await self.send_json(
                    {"error": "File messages must be sent via the REST API."}
                )
                return
        else:
            # Save text message to database
            message_data = await self.save_message(message_type, text)

        # Broadcast to the room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": message_data,
            },
        )

    async def chat_message(self, event):
        """Receive message from room group and send to WebSocket."""
        await self.send_json(event["message"])

    # ---- Database helpers ----

    @database_sync_to_async
    def get_chatroom(self):
        try:
            return ChatRoom.objects.select_related("sender", "receiver").get(
                pk=self.chatroom_id
            )
        except (ChatRoom.DoesNotExist, ValueError):
            return None

    @database_sync_to_async
    def is_participant(self):
        return self.chatroom.has_participant(self.user)

    @database_sync_to_async
    def check_is_staff(self):
        return self.user.is_staff

    @database_sync_to_async
    def check_chatroom_active(self):
        return ChatRoom.objects.filter(pk=self.chatroom_id, is_active=True).exists()

    @database_sync_to_async
    def save_message(self, message_type, text):
        message = Message.objects.create(
            chatroom=self.chatroom,
            sender=self.user,
            message_type=message_type,
            text=text,
        )
        return {
            "id": str(message.id),
            "chatroom": str(message.chatroom_id),
            "sender": {
                "id": str(self.user.id),
                "full_name": self.user.full_name,
                "username": self.user.username,
                "profile_image_url": self.user.profile_image_url,
            },
            "message_type": message.message_type,
            "text": message.text,
            "file": None,
            "created_at": message.created_at.isoformat(),
            "is_deleted": False,
        }

    @database_sync_to_async
    def get_existing_message(self, message_id):
        try:
            message = Message.objects.select_related("sender").get(
                pk=message_id,
                chatroom=self.chatroom,
                sender=self.user,
            )
            return {
                "id": str(message.id),
                "chatroom": str(message.chatroom_id),
                "sender": {
                    "id": str(message.sender.id),
                    "full_name": message.sender.full_name,
                    "username": message.sender.username,
                    "profile_image_url": message.sender.profile_image_url,
                },
                "message_type": message.message_type,
                "text": message.text,
                "file": message.file,
                "created_at": message.created_at.isoformat(),
                "is_deleted": message.is_deleted,
            }
        except (Message.DoesNotExist, ValueError):
            return None
