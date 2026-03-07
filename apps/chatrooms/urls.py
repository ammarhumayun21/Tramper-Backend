"""
URL configuration for the chatrooms app.
"""

from django.urls import path

from .views import ChatRoomListView, SendMessageView, DisableChatRoomView, EnableChatRoomView

urlpatterns = [
    path("", ChatRoomListView.as_view(), name="chatroom-list"),
    path("<uuid:pk>/send/", SendMessageView.as_view(), name="chatroom-send"),
    path("<uuid:pk>/disable/", DisableChatRoomView.as_view(), name="chatroom-disable"),
    path("<uuid:pk>/enable/", EnableChatRoomView.as_view(), name="chatroom-enable"),
]
