"""
URL configuration for the chatrooms app.
"""

from django.urls import path

from .views import ChatRoomListView, ChatRoomMessagesView, SendMessageView, DisableChatRoomView, UnreadCountView, MarkMessagesSeenView

urlpatterns = [
    path("", ChatRoomListView.as_view(), name="chatroom-list"),
    path("unread/", UnreadCountView.as_view(), name="chatroom-unread"),
    path("<uuid:pk>/messages/", ChatRoomMessagesView.as_view(), name="chatroom-messages"),
    path("<uuid:pk>/send/", SendMessageView.as_view(), name="chatroom-send"),
    path("<uuid:pk>/seen/", MarkMessagesSeenView.as_view(), name="chatroom-seen"),
    path("<uuid:pk>/disable/", DisableChatRoomView.as_view(), name="chatroom-disable"),
]
