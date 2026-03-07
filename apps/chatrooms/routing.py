"""
WebSocket URL routing for the chatrooms app.
"""

from django.urls import re_path

from .consumers import ChatConsumer, UserConsumer

websocket_urlpatterns = [
    re_path(r"ws/user/$", UserConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<chatroom_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
]
