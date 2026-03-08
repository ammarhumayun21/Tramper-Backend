"""
WebSocket URL routing for the chatrooms app.
"""

from django.urls import re_path

from .consumers import UserConsumer

websocket_urlpatterns = [
    re_path(r"ws/user/$", UserConsumer.as_asgi()),
]
