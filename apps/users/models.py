"""
Custom User model for Tramper.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Email address is required."))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model based on Dart UserModel schema.
    Email-based authentication.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    full_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("full name"),
    )

    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("username"),
    )

    email = models.EmailField(
        unique=True,
        verbose_name=_("email address"),
    )

    is_email_verified = models.BooleanField(
        default=False,
        verbose_name=_("email verified"),
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("phone number"),
    )

    is_phone_verified = models.BooleanField(
        default=False,
        verbose_name=_("phone verified"),
    )

    profile_image_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("profile image URL"),
    )

    address = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("address"),
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("city"),
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("country"),
    )

    bio = models.TextField(
        blank=True,
        verbose_name=_("bio"),
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name=_("rating"),
    )

    total_trips = models.PositiveIntegerField(
        default=0,
        verbose_name=_("total trips"),
    )

    total_deals = models.PositiveIntegerField(
        default=0,
        verbose_name=_("total deals"),
    )

    total_shipments = models.PositiveIntegerField(
        default=0,
        verbose_name=_("total shipments"),
    )

    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("staff status"),
    )

    is_user_verified = models.BooleanField(
        default=False,
        verbose_name=_("user verified"),
        help_text=_("Designates whether the user has been identity-verified by admin."),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name or self.username} ({self.email})"

    def get_full_name(self):
        return self.full_name or self.username

    def get_short_name(self):
        return self.username


class PasswordResetToken(models.Model):
    """Token for password reset functionality."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name=_("user"),
    )

    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("token"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
    )

    is_used = models.BooleanField(
        default=False,
        verbose_name=_("is used"),
    )

    class Meta:
        verbose_name = _("password reset token")
        verbose_name_plural = _("password reset tokens")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reset token for {self.user.email}"


class UserSettings(models.Model):
    """
    User settings model for Tramper.
    Linked one-to-one with User model.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name=_("user"),
    )

    matchmaking_notifications_enabled = models.BooleanField(
        default=False,
        verbose_name=_("matchmaking notifications enabled"),
    )

    chat_notifications_enabled = models.BooleanField(
        default=False,
        verbose_name=_("chat notifications enabled"),
    )

    selected_language_code = models.CharField(
        max_length=10,
        default="en",
        verbose_name=_("selected language code"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("user settings")
        verbose_name_plural = _("user settings")

    def __str__(self):
        return f"Settings for {self.user.email}"


class EmailVerificationToken(models.Model):
    """Token for email address verification."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
        verbose_name=_("user"),
    )

    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("token"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
    )

    is_used = models.BooleanField(
        default=False,
        verbose_name=_("is used"),
    )

    class Meta:
        verbose_name = _("email verification token")
        verbose_name_plural = _("email verification tokens")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Email verification token for {self.user.email}"
