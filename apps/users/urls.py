"""
Authentication URLs for Tramper.
"""

from django.urls import path
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
    CurrentUserView,
    CurrentUserSettingsView,
    AllUsersView,
)
from core.api import success_response


# Wrap TokenRefreshView with proper schema and success_response
class TokenRefreshViewWithSchema(TokenRefreshView):
    @extend_schema(
        tags=["Authentication"],
        summary="Refresh access token",
        description="Generate a new access token using a valid refresh token.",
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            return success_response(response.data)
        return response

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshViewWithSchema.as_view(), name="token_refresh"),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("me/settings/", CurrentUserSettingsView.as_view(), name="current_user_settings"),
    path("users/", AllUsersView.as_view(), name="all_users"),
]