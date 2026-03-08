"""
WebSocket consumer for real-time chat messaging.

UserConsumer: Unified user WebSocket (ws/user/)
  - On connect: sends chatroom list with unread counts
  - Receives live chatroom_update events
  - Handles join_chat / leave_chat to enter/exit chatrooms
  - Handles send_message for text messages
  - Handles load_more for older message pagination
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.db.models import Q

from .models import ChatRoom, Message


def _serialize_user(user):
    """Serialize a user object to a dict."""
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "username": user.username,
        "profile_image_url": user.profile_image_url,
        "rating": str(user.rating) if user.rating else None,
    }


def _serialize_message(message, sender_override=None):
    """Serialize a message object to a dict."""
    sender = sender_override or message.sender
    return {
        "id": str(message.id),
        "chatroom": str(message.chatroom_id),
        "sender": _serialize_user(sender),
        "message_type": message.message_type,
        "text": message.text,
        "file": message.file,
        "created_at": message.created_at.isoformat(),
        "is_deleted": message.is_deleted,
        "is_seen": message.is_seen,
    }


def _build_chatroom_update(room, user):
    """Build a chatroom_update payload for a specific user."""
    last_msg = (
        room.messages.filter(is_deleted=False)
        .order_by("-created_at")
        .select_related("sender")
        .first()
    )
    last_message_data = None
    if last_msg:
        last_message_data = {
            "id": str(last_msg.id),
            "sender_id": str(last_msg.sender_id),
            "message_type": last_msg.message_type,
            "text": last_msg.text,
            "created_at": last_msg.created_at.isoformat(),
        }
    unread_count = (
        room.messages.filter(is_seen=False, is_deleted=False)
        .exclude(sender=user)
        .count()
    )
    return {
        "id": str(room.id),
        "last_message": last_message_data,
        "unread_count": unread_count,
    }


class UserConsumer(AsyncJsonWebsocketConsumer):
    """
    Unified user WebSocket consumer.

    Connection: ws/user/?token=<jwt>

    On connect:
      - Sends full chatroom list with last message and unread counts.

    Actions (client → server):
      - {"action": "refresh"}
          Re-sends chatroom list.
      - {"action": "join_chat", "chatroom_id": "<uuid>"}
          Joins a chatroom: sends message_history, marks messages as seen.
      - {"action": "leave_chat"}
          Leaves the currently joined chatroom.
      - {"action": "send_message", "message_type": "text", "text": "..."}
          Sends a text message in the joined chatroom.
      - {"action": "send_message", "message_type": "image|video|file", "message_id": "<uuid>"}
          Broadcasts a file message (already created via REST API).
      - {"action": "load_more", "before": "<message_id>"}
          Loads older messages before the given message ID.

    Server → client events:
      - chatroom_list, chatroom_update, messages_seen
      - message_history, new_message, load_more_messages
    """

    async def connect(self):
        self.user = self.scope.get("user", AnonymousUser())

        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_group_name = f"user_{self.user.id}"
        self.is_admin = await self._check_is_staff()

        # Chat state — set when user joins a chatroom
        self.chatroom = None
        self.chatroom_id = None
        self.room_group_name = None

        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        # Send chatroom list
        chatrooms = await self._get_chatroom_list()
        await self.send_json({
            "type": "chatroom_list",
            "chatrooms": chatrooms,
        })

    async def disconnect(self, close_code):
        # Leave chat room group if joined
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        # Leave user group
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )
        # Release DB connection held by this consumer
        await database_sync_to_async(close_old_connections)()

    async def receive_json(self, content, **kwargs):
        """Route incoming actions."""
        action = content.get("action")

        if action == "refresh":
            chatrooms = await self._get_chatroom_list()
            await self.send_json({
                "type": "chatroom_list",
                "chatrooms": chatrooms,
            })

        elif action == "join_chat":
            await self._handle_join_chat(content)

        elif action == "leave_chat":
            await self._handle_leave_chat()

        elif action == "send_message":
            await self._handle_send_message(content)

        elif action == "load_more":
            await self._handle_load_more(content)

    # ---- Channel-layer event handlers ----

    async def chatroom_update(self, event):
        """Forward chatroom_update from channel layer to client."""
        await self.send_json({
            "type": "chatroom_update",
            "chatroom": event["chatroom"],
        })

    async def messages_seen(self, event):
        """Notify client that messages in a chatroom were marked as seen."""
        await self.send_json({
            "type": "messages_seen",
            "chatroom_id": event["chatroom_id"],
        })

    async def chat_message(self, event):
        """Receive new message from room group and send to WebSocket."""
        await self.send_json({
            "type": "new_message",
            "message": event["message"],
        })

    # ---- Action handlers ----

    async def _handle_join_chat(self, content):
        """Join a chatroom: validate, send history, mark seen."""
        chatroom_id = content.get("chatroom_id")
        if not chatroom_id:
            await self.send_json({"error": "chatroom_id is required."})
            return

        # Leave previous room if any
        await self._handle_leave_chat()

        # Fetch and validate
        chatroom = await self._get_chatroom(chatroom_id)
        if chatroom is None:
            await self.send_json({"type": "error", "error": "Chatroom not found.", "code": 4404})
            return

        if not self.is_admin and not await self._is_participant(chatroom):
            await self.send_json({"type": "error", "error": "Not a participant.", "code": 4403})
            return

        if not self.is_admin and not chatroom.is_active:
            await self.send_json({"type": "error", "error": "Chatroom is disabled.", "code": 4403})
            return

        # Store chat state
        self.chatroom = chatroom
        self.chatroom_id = str(chatroom.pk)
        self.room_group_name = f"chat_{self.chatroom_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Send message history (last 50)
        messages = await self._get_message_history(limit=50)
        await self.send_json({
            "type": "message_history",
            "chatroom_id": self.chatroom_id,
            "messages": messages,
            "has_more": len(messages) == 50,
        })

        # Auto-mark unseen messages as seen (non-admin only)
        if not self.is_admin:
            marked_count = await self._mark_messages_seen()
            if marked_count > 0:
                other_user_id = await self._get_other_user_id()
                if other_user_id:
                    await self.channel_layer.group_send(
                        f"user_{other_user_id}",
                        {
                            "type": "messages.seen",
                            "chatroom_id": self.chatroom_id,
                        },
                    )

    async def _handle_leave_chat(self):
        """Leave the currently joined chatroom."""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        self.chatroom = None
        self.chatroom_id = None
        self.room_group_name = None

    async def _handle_send_message(self, content):
        """Send a message in the joined chatroom."""
        if not self.chatroom:
            await self.send_json({"error": "Join a chatroom first."})
            return

        # Admin monitors are read-only
        if self.is_admin:
            await self.send_json({"error": "Admin monitoring mode — sending messages is disabled."})
            return

        # Re-check chatroom is still active
        is_active = await self._check_chatroom_active()
        if not is_active:
            await self.send_json({"error": "Chatroom is disabled. You cannot send messages."})
            return

        message_type = content.get("message_type", "text")
        text = content.get("text", "")

        if message_type not in ("text", "image", "video", "file"):
            await self.send_json({"error": "Invalid message type."})
            return

        if message_type == "text" and (not text or not text.strip()):
            await self.send_json({"error": "Text is required for text messages."})
            return

        # File-based messages must reference an existing message created via REST
        if message_type in ("image", "video", "file"):
            message_id = content.get("message_id")
            if message_id:
                message_data = await self._get_existing_message(message_id)
                if message_data is None:
                    await self.send_json({"error": "Message not found."})
                    return
            else:
                await self.send_json({"error": "File messages must be sent via the REST API."})
                return
        else:
            message_data = await self._save_message(message_type, text)

        # Broadcast to the room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": message_data,
            },
        )

        # Push chatroom_update to both users' global groups
        await self._push_chatroom_updates()

    async def _handle_load_more(self, content):
        """Load older messages in the joined chatroom."""
        if not self.chatroom:
            await self.send_json({"error": "Join a chatroom first."})
            return

        before = content.get("before")
        if not before:
            await self.send_json({"error": "'before' message ID is required."})
            return

        messages = await self._get_message_history(limit=50, before_id=before)
        await self.send_json({
            "type": "load_more_messages",
            "chatroom_id": self.chatroom_id,
            "messages": messages,
            "has_more": len(messages) == 50,
        })

    # ---- Database helpers ----

    @database_sync_to_async
    def _check_is_staff(self):
        return self.user.is_staff

    @database_sync_to_async
    def _get_chatroom_list(self):
        user = self.user
        chatrooms = (
            ChatRoom.objects.filter(Q(sender=user) | Q(receiver=user))
            .select_related("sender", "receiver", "request")
            .order_by("-created_at")
        )

        result = []
        for room in chatrooms:
            last_msg = (
                room.messages.filter(is_deleted=False)
                .order_by("-created_at")
                .select_related("sender")
                .first()
            )
            unread_count = (
                room.messages.filter(is_seen=False, is_deleted=False)
                .exclude(sender=user)
                .count()
            )
            last_message_data = None
            if last_msg:
                last_message_data = {
                    "id": str(last_msg.id),
                    "sender_id": str(last_msg.sender_id),
                    "message_type": last_msg.message_type,
                    "text": last_msg.text,
                    "created_at": last_msg.created_at.isoformat(),
                }

            result.append({
                "id": str(room.id),
                "sender": _serialize_user(room.sender),
                "receiver": _serialize_user(room.receiver),
                "request_id": str(room.request_id),
                "is_active": room.is_active,
                "created_at": room.created_at.isoformat(),
                "last_message": last_message_data,
                "unread_count": unread_count,
            })

        return result

    @database_sync_to_async
    def _get_chatroom(self, chatroom_id):
        try:
            return ChatRoom.objects.select_related("sender", "receiver").get(
                pk=chatroom_id
            )
        except (ChatRoom.DoesNotExist, ValueError):
            return None

    @database_sync_to_async
    def _is_participant(self, chatroom):
        return chatroom.has_participant(self.user)

    @database_sync_to_async
    def _check_chatroom_active(self):
        return ChatRoom.objects.filter(pk=self.chatroom_id, is_active=True).exists()

    @database_sync_to_async
    def _get_message_history(self, limit=50, before_id=None):
        qs = Message.objects.filter(
            chatroom_id=self.chatroom_id, is_deleted=False
        ).select_related("sender").order_by("-created_at")

        if before_id:
            try:
                before_msg = Message.objects.get(pk=before_id)
                qs = qs.filter(created_at__lt=before_msg.created_at)
            except (Message.DoesNotExist, ValueError):
                return []

        messages = list(qs[:limit])
        messages.reverse()  # chronological order
        return [_serialize_message(m) for m in messages]

    @database_sync_to_async
    def _mark_messages_seen(self):
        return Message.objects.filter(
            chatroom_id=self.chatroom_id,
            is_seen=False,
            is_deleted=False,
        ).exclude(sender=self.user).update(is_seen=True)

    @database_sync_to_async
    def _get_other_user_id(self):
        if str(self.chatroom.sender_id) == str(self.user.id):
            return str(self.chatroom.receiver_id)
        return str(self.chatroom.sender_id)

    @database_sync_to_async
    def _save_message(self, message_type, text):
        message = Message.objects.create(
            chatroom=self.chatroom,
            sender=self.user,
            message_type=message_type,
            text=text,
        )
        return _serialize_message(message, sender_override=self.user)

    @database_sync_to_async
    def _get_existing_message(self, message_id):
        try:
            message = Message.objects.select_related("sender").get(
                pk=message_id,
                chatroom=self.chatroom,
                sender=self.user,
            )
            return _serialize_message(message)
        except (Message.DoesNotExist, ValueError):
            return None

    async def _push_chatroom_updates(self):
        """Push chatroom_update to both users' global WS groups."""
        sender_id = str(self.chatroom.sender_id)
        receiver_id = str(self.chatroom.receiver_id)

        for uid in (sender_id, receiver_id):
            update = await self._build_update_for_user(uid)
            await self.channel_layer.group_send(
                f"user_{uid}",
                {
                    "type": "chatroom.update",
                    "chatroom": update,
                },
            )

    @database_sync_to_async
    def _build_update_for_user(self, user_id):
        """Build chatroom_update payload scoped to a specific user's unread count."""
        room = self.chatroom
        last_msg = (
            room.messages.filter(is_deleted=False)
            .order_by("-created_at")
            .select_related("sender")
            .first()
        )
        last_message_data = None
        if last_msg:
            last_message_data = {
                "id": str(last_msg.id),
                "sender_id": str(last_msg.sender_id),
                "message_type": last_msg.message_type,
                "text": last_msg.text,
                "created_at": last_msg.created_at.isoformat(),
            }
        unread_count = (
            room.messages.filter(is_seen=False, is_deleted=False)
            .exclude(sender_id=user_id)
            .count()
        )
        return {
            "id": str(room.id),
            "last_message": last_message_data,
            "unread_count": unread_count,
        }
