"""
Chatroom and Message models for Tramper.
Handles private chat between two users linked to a request.
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ChatRoom(models.Model):
    """
    Private chatroom between two users, created when a request is accepted.
    Automatically disabled when the associated shipment is received.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatrooms_as_sender",
        verbose_name=_("sender"),
        help_text=_("The user who sent the original request"),
    )

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chatrooms_as_receiver",
        verbose_name=_("receiver"),
        help_text=_("The user who received the original request"),
    )

    request = models.OneToOneField(
        "requests.Request",
        on_delete=models.CASCADE,
        related_name="chatroom",
        verbose_name=_("request"),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("is active"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    disabled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("disabled at"),
    )

    class Meta:
        verbose_name = _("chatroom")
        verbose_name_plural = _("chatrooms")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender", "receiver"], name="chatroom_participants_idx"),
            models.Index(fields=["is_active"], name="chatroom_active_idx"),
        ]

    def __str__(self):
        return f"ChatRoom: {self.sender} ↔ {self.receiver}"

    def has_participant(self, user):
        """Check if a user is a participant of this chatroom."""
        return self.sender_id == user.id or self.receiver_id == user.id


class Message(models.Model):
    """
    A message within a chatroom. Supports text, image, video, and file types.
    File-based messages are uploaded via S3.
    """

    MESSAGE_TYPE_CHOICES = [
        ("text", _("Text")),
        ("image", _("Image")),
        ("video", _("Video")),
        ("file", _("File")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    chatroom = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("chatroom"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name=_("sender"),
    )

    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
        verbose_name=_("message type"),
    )

    text = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("text"),
    )

    file = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("file"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_("is deleted"),
    )

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["chatroom", "created_at"], name="msg_chatroom_time_idx"),
            models.Index(fields=["is_deleted"], name="msg_deleted_idx"),
        ]

    def __str__(self):
        return f"{self.sender} [{self.message_type}] in {self.chatroom_id}"
