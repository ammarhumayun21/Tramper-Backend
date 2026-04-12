"""
Cache invalidation signals for translations.
"""

from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Translation, Language


@receiver(post_save, sender=Translation)
@receiver(post_delete, sender=Translation)
def invalidate_translation_cache(sender, instance, **kwargs):
    """Clear cached translations when a translation is created, updated, or deleted."""
    cache_key = f"translations_{instance.language.code}"
    cache.delete(cache_key)


@receiver(post_save, sender=Language)
@receiver(post_delete, sender=Language)
def invalidate_language_cache(sender, instance, **kwargs):
    """Clear cached translations for a language when it changes."""
    cache_key = f"translations_{instance.code}"
    cache.delete(cache_key)
