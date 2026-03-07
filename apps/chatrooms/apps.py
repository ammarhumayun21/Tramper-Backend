from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ChatroomsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chatrooms"
    verbose_name = _("Chatrooms")

    def ready(self):
        import apps.chatrooms.signals  # noqa: F401
