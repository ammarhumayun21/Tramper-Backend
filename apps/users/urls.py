"""
Authentication URLs for Tramper.
"""

from django.urls import path
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

# Wrap TokenRefreshView with proper schema
class TokenRefreshViewWithSchema(TokenRefreshView):
    @extend_schema(
        tags=["Authentication"],
        summary="Refresh access token",
        description="Generate a new access token using a valid refresh token.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

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