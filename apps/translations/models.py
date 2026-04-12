"""
Translation models for Tramper i18n system.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Language(models.Model):
    """Supported language for translations."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True,
        verbose_name=_("language code"),
        help_text=_("ISO 639-1 code (e.g., en, ar)"),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("language name"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        ordering = ["code"]
        verbose_name = _("language")
        verbose_name_plural = _("languages")

    def __str__(self):
        return f"{self.name} ({self.code})"


class Translation(models.Model):
    """Key-value translation entry for a specific language."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("language"),
    )
    key = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name=_("translation key"),
        help_text=_("Namespaced key (e.g., navbar.home, auth.login)"),
    )
    value = models.TextField(
        verbose_name=_("translation value"),
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
        ordering = ["key"]
        verbose_name = _("translation")
        verbose_name_plural = _("translations")
        constraints = [
            models.UniqueConstraint(
                fields=["language", "key"],
                name="unique_language_key",
            ),
        ]

    def __str__(self):
        return f"{self.language.code}:{self.key}"
