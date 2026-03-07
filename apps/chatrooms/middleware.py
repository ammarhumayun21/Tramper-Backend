"""
JWT authentication middleware for Django Channels WebSocket connections.
Extracts token from query string: ws://.../?token=<jwt_access_token>
"""

from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate JWT access token and return the corresponding user."""
    try:
        token = AccessToken(token_str)
        return User.objects.get(id=token["user_id"])
    except Exception:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections via JWT
    token passed as a query parameter or HTTP-only cookie.
    """

    async def __call__(self, scope, receive, send):
        # Try query string token first
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token_list = query_params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            # Fall back to access_token cookie (used by admin panel)
            cookie_header = dict(scope.get("headers", [])).get(b"cookie", b"").decode("utf-8")
            if cookie_header:
                cookies = SimpleCookie(cookie_header)
                access_morsel = cookies.get("access_token")
                if access_morsel:
                    scope["user"] = await get_user_from_token(access_morsel.value)
                else:
                    scope["user"] = AnonymousUser()
            else:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
