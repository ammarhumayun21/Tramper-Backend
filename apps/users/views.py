"""
Authentication views for Tramper.
JWT-based authentication with drf-spectacular documentation.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from core.api import success_response
from core.emails.welcome import send_welcome_email
from core.emails.password_reset import send_password_reset_email


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a new user",
        description="Create a new user account and receive JWT tokens.",
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(response=UserSerializer, description="User registered successfully."),
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        send_welcome_email(user)
        return success_response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Login user",
        description="Authenticate user and receive JWT tokens.",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer, description="Login successful."),
            400: OpenApiResponse(description="Invalid credentials."),
        },
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return success_response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            }
        )


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Request password reset",
        description="Send password reset email to user.",
        request=PasswordResetRequestSerializer,
        responses={200: OpenApiResponse(description="Password reset email sent.")},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.save()
        if reset_token:
            send_password_reset_email(reset_token.user, reset_token.token)
        return success_response(
            {"message": "If an account with this email exists, you will receive a password reset link."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Confirm password reset",
        description="Reset password using token.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully."),
            400: OpenApiResponse(description="Invalid or expired token."),
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({"message": "Password has been reset successfully."})
