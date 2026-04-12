"""
Admin configuration for translations.
"""

from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html

from .models import Language, Translation


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["code"]
    readonly_fields = ["id", "created_at"]


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ["key", "language", "value_preview", "updated_at"]
    list_filter = ["language"]
    search_fields = ["key", "value"]
    list_editable = []
    ordering = ["key", "language"]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_per_page = 50
    list_select_related = ["language"]
    autocomplete_fields = ["language"]
    actions = ["clear_translation_cache"]

    def value_preview(self, obj):
        """Show truncated value in list view."""
        text = obj.value[:80]
        if len(obj.value) > 80:
            text += "..."
        return text

    value_preview.short_description = "Value"

    @admin.action(description="Clear translation cache for selected items")
    def clear_translation_cache(self, request, queryset):
        lang_codes = set(queryset.values_list("language__code", flat=True))
        for code in lang_codes:
            cache.delete(f"translations_{code}")
        self.message_user(request, f"Cleared cache for: {', '.join(lang_codes)}")
