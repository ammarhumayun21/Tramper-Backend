"""
Authentication serializers for Tramper.
JWT-based authentication with i18n support.
"""

import secrets
from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, PasswordResetToken, UserSettings


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (admin view)."""

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "username",
            "email",
            "is_email_verified",
            "phone",
            "is_phone_verified",
            "profile_image_url",
            "is_active",
            "is_staff",
            "is_superuser",
            "rating",
            "total_trips",
            "total_deals",
            "total_shipments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "username",
            "email",
            "is_email_verified",
            "phone",
            "is_phone_verified",
            "profile_image_url",
            "address",
            "city",
            "country",
            "bio",
            "rating",
            "total_trips",
            "total_deals",
            "total_shipments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_email_verified",
            "is_phone_verified",
            "profile_image_url",
            "rating",
            "total_trips",
            "total_deals",
            "total_shipments",
            "created_at",
            "updated_at",
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text=_("Password must be at least 8 characters."),
    )

    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text=_("Confirm your password."),
    )

    profile_image = serializers.ImageField(
        write_only=True,
        required=False,
        help_text=_("User profile image (will be uploaded to S3)."),
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "full_name",
            "password",
            "password_confirm",
            "phone",
            "profile_image",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
            "full_name": {"required": False},
            "phone": {"required": False},
        }

    def validate_email(self, value):
        """Validate email uniqueness."""
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists.")
            )
        return email

    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        return value

    def validate_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value

    def validate(self, attrs):
        """Validate passwords match."""
        if attrs.get("password") != attrs.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": _("Passwords do not match.")}
            )
        return attrs

    def create(self, validated_data):
        """Create user with hashed password."""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField(
        required=True,
        help_text=_("Email address."),
    )

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("Password."),
    )

    def validate_email(self, value):
        """Normalize email."""
        return value.lower()

    def validate(self, attrs):
        """Authenticate user."""
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError(
                {"detail": _("Invalid email or password.")}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": _("User account is disabled.")}
            )

        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField(
        required=True,
        help_text=_("Email address associated with your account."),
    )

    def validate_email(self, value):
        """Normalize email."""
        return value.lower()

    def validate(self, attrs):
        """Check if user exists and add to validated data."""
        email = attrs.get("email")
        
        try:
            user = User.objects.get(email=email)
            attrs["user"] = user
        except User.DoesNotExist:
            # Don't raise error to prevent email enumeration
            attrs["user"] = None
        
        return attrs

    def create(self, validated_data):
        """Create password reset token."""
        user = validated_data.get("user")
        
        if not user:
            # This should not be called if user is None
            raise serializers.ValidationError("User not found")

        # Invalidate previous tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)

        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
        )

        return reset_token


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField(
        required=True,
        help_text=_("Password reset token."),
    )

    new_password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("New password."),
    )

    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text=_("Confirm new password."),
    )

    def validate_new_password(self, value):
        """Validate password strength."""
        validate_password(value)
        return value

    def validate(self, attrs):
        """Validate token and passwords."""
        token = attrs.get("token")
        new_password = attrs.get("new_password")
        new_password_confirm = attrs.get("new_password_confirm")

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")}
            )

        try:
            reset_token = PasswordResetToken.objects.get(
                token=token,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(
                {"token": _("Invalid or expired token.")}
            )

        attrs["reset_token"] = reset_token
        return attrs

    def save(self):
        """Reset password."""
        reset_token = self.validated_data["reset_token"]
        new_password = self.validated_data["new_password"]

        user = reset_token.user
        user.set_password(new_password)
        user.save()

        reset_token.is_used = True
        reset_token.save()

        return user


class UserSettingsSerializer(serializers.ModelSerializer):
    """Serializer for user settings."""

    class Meta:
        model = UserSettings
        fields = [
            "id",
            "matchmaking_notifications_enabled",
            "chat_notifications_enabled",
            "selected_language_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    profile_image = serializers.ImageField(
        write_only=True,
        required=False,
        help_text=_("User profile image (will be uploaded to S3)."),
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "username",
            "phone",
            "address",
            "city",
            "country",
            "bio",
            "profile_image",
        ]
        extra_kwargs = {
            "username": {"required": False},
        }

    def validate_username(self, value):
        """Validate username uniqueness (exclude current user)."""
        user = self.instance
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                _("A user with this username already exists.")
            )
        return value

