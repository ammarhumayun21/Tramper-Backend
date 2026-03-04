"""
Admin Panel app configuration for Tramper.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_panel"
    verbose_name = _("Admin Panel")

    def ready(self):
        import apps.admin_panel.signals  # noqa: F401
