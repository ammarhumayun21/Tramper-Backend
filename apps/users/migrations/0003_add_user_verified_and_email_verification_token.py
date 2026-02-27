# Generated migration for adding is_user_verified flag and EmailVerificationToken model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_usersettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_user_verified",
            field=models.BooleanField(
                default=False,
                help_text="Designates whether the user has been identity-verified by admin.",
                verbose_name="user verified",
            ),
        ),
        migrations.CreateModel(
            name="EmailVerificationToken",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "token",
                    models.CharField(
                        max_length=100,
                        unique=True,
                        verbose_name="token",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="created at",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        verbose_name="expires at",
                    ),
                ),
                (
                    "is_used",
                    models.BooleanField(
                        default=False,
                        verbose_name="is used",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_verification_tokens",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "email verification token",
                "verbose_name_plural": "email verification tokens",
                "ordering": ["-created_at"],
            },
        ),
    ]
