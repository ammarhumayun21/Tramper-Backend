"""
URL configuration for the chatrooms app.
"""

from django.urls import path

from .views import ChatRoomListView, ChatRoomMessagesView, SendMessageView

urlpatterns = [
    path("", ChatRoomListView.as_view(), name="chatroom-list"),
    path("<uuid:pk>/messages/", ChatRoomMessagesView.as_view(), name="chatroom-messages"),
    path("<uuid:pk>/send/", SendMessageView.as_view(), name="chatroom-send"),
]
