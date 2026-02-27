# Initial migration for verification center app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VerificationRequest",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "id_card_front_url",
                    models.URLField(
                        max_length=500,
                        help_text="URL of uploaded front side of ID card",
                        verbose_name="ID card front image URL",
                    ),
                ),
                (
                    "id_card_back_url",
                    models.URLField(
                        max_length=500,
                        help_text="URL of uploaded back side of ID card",
                        verbose_name="ID card back image URL",
                    ),
                ),
                (
                    "selfie_with_id_url",
                    models.URLField(
                        max_length=500,
                        help_text="URL of uploaded selfie holding ID card",
                        verbose_name="selfie with ID image URL",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(                        blank=True,                        max_length=20,
                        help_text="Phone number submitted for verification",
                        verbose_name="phone number",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "admin_notes",
                    models.TextField(
                        blank=True,
                        help_text="Notes from admin during review",
                        verbose_name="admin notes",
                    ),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name="reviewed at",
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
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="updated at",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification_requests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_verifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reviewed by",
                    ),
                ),
            ],
            options={
                "verbose_name": "verification request",
                "verbose_name_plural": "verification requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
