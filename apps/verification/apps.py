"""
Verification center app configuration.
"""

from django.apps import AppConfig


class VerificationConfig(AppConfig):
    """Configuration for verification center app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.verification"
    verbose_name = "Verification Center"
