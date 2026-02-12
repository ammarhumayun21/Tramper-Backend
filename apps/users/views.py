"""
Authentication views for Tramper.
JWT-based authentication with drf-spectacular documentation.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, UserSettings
from .serializers import (
    UserSerializer,
    UserListSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserSettingsSerializer,
    UserUpdateSerializer,
)
from core.api import success_response
from core.emails.welcome import send_welcome_email
from core.emails.password_reset import send_password_reset_email
from core.storage import s3_storage
from core.parsers import NestedMultiPartParser, NestedFormParser


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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
        
        # Extract profile_image from validated data if present
        profile_image = serializer.validated_data.pop('profile_image', None)
        
        # Create user
        user = serializer.save()
        
        # Upload profile image to S3 if provided
        if profile_image:
            try:
                profile_image_url = s3_storage.upload_image(profile_image, folder="profile_images")
                user.profile_image_url = profile_image_url
                user.save(update_fields=['profile_image_url'])
            except Exception as e:
                # Log error but don't fail registration
                print(f"Failed to upload profile image: {str(e)}")

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
        
        # Only call save() if user exists (to avoid DRF assertion error)
        if serializer.validated_data.get("user"):
            reset_token = serializer.save()
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


class CurrentUserView(APIView):
    """Get current authenticated user."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=["Users"],
        summary="Get current user",
        description="Get the currently authenticated user's profile.",
        responses={
            200: OpenApiResponse(response=UserSerializer, description="Current user data."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Update current user profile",
        description="Update the currently authenticated user's profile.",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UserSerializer, description="Updated user data."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Extract profile_image if present
        profile_image = serializer.validated_data.pop('profile_image', None)
        
        # Update user
        user = serializer.save()
        
        # Upload profile image to S3 if provided
        if profile_image:
            try:
                profile_image_url = s3_storage.upload_image(profile_image, folder="avatars")
                user.profile_image_url = profile_image_url
                user.save(update_fields=['profile_image_url'])
            except Exception as e:
                # Log error but don't fail update
                print(f"Failed to upload profile image: {str(e)}")
        
        return success_response(UserSerializer(user).data)


class CurrentUserSettingsView(APIView):
    """Get and update current user settings."""
    permission_classes = [IsAuthenticated]

    def get_or_create_settings(self, user):
        """Get or create settings for user."""
        settings, _ = UserSettings.objects.get_or_create(user=user)
        return settings

    @extend_schema(
        tags=["Users"],
        summary="Get current user settings",
        description="Get the currently authenticated user's settings.",
        responses={
            200: OpenApiResponse(response=UserSettingsSerializer, description="Current user settings."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def get(self, request):
        settings = self.get_or_create_settings(request.user)
        serializer = UserSettingsSerializer(settings)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Users"],
        summary="Update current user settings",
        description="Update the currently authenticated user's settings.",
        request=UserSettingsSerializer,
        responses={
            200: OpenApiResponse(response=UserSettingsSerializer, description="Updated user settings."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def patch(self, request):
        settings = self.get_or_create_settings(request.user)
        serializer = UserSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data)


class AllUsersView(ListAPIView):
    """
    List all users (superuser only).
    """
    permission_classes = [IsAdminUser]
    serializer_class = UserListSerializer
    queryset = User.objects.all().order_by('-created_at')

    @extend_schema(
        tags=["Users"],
        summary="List all users",
        description="Get a list of all users. Only accessible by superusers.",
        responses={
            200: OpenApiResponse(response=UserListSerializer(many=True), description="List of all users."),
            401: OpenApiResponse(description="Not authenticated."),
            403: OpenApiResponse(description="Not authorized (superuser only)."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
