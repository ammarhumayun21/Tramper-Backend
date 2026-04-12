"""
Translation API views for Tramper i18n system.
Reads language from request headers, never from server/system language.
"""

from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from core.api import success_response

from .models import Language, Translation


CACHE_TTL = 60 * 60  # 1 hour


class TranslationsView(APIView):
    """
    GET /api/v1/translations/

    Returns flat JSON of translation key-value pairs for the requested language.
    Language is determined strictly from request headers:
      1. Accept-Language header (primary)
      2. X-Language header (fallback)
      3. "en" (default fallback)
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        lang_code = self._get_language(request)
        cache_key = f"translations_{lang_code}"

        translations = cache.get(cache_key)
        if translations is None:
            qs = Translation.objects.filter(
                language__code=lang_code,
                language__is_active=True,
            ).values_list("key", "value")

            translations = dict(qs)

            # If requested language has no translations, fallback to English
            if not translations and lang_code != "en":
                lang_code = "en"
                cache_key = f"translations_{lang_code}"
                translations = cache.get(cache_key)
                if translations is None:
                    qs = Translation.objects.filter(
                        language__code="en",
                        language__is_active=True,
                    ).values_list("key", "value")
                    translations = dict(qs)
                    cache.set(cache_key, translations, CACHE_TTL)
            else:
                cache.set(cache_key, translations, CACHE_TTL)

        return success_response(translations)

    def _get_language(self, request):
        """
        Extract language code from request headers.
        Priority: Accept-Language > X-Language > "en"
        """
        # 1. Accept-Language header
        accept_lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        if accept_lang:
            # Parse first language code: "ar-SA,ar;q=0.9,en;q=0.8" → "ar"
            lang = accept_lang.split(",")[0].split(";")[0].strip().split("-")[0].lower()
            if lang and self._is_valid_language(lang):
                return lang

        # 2. X-Language header
        x_lang = request.META.get("HTTP_X_LANGUAGE", "")
        if x_lang:
            lang = x_lang.strip().lower()
            if self._is_valid_language(lang):
                return lang

        # 3. Default fallback
        return "en"

    def _is_valid_language(self, code):
        """Check if a language code exists and is active."""
        return Language.objects.filter(code=code, is_active=True).exists()


class LanguagesListView(APIView):
    """
    GET /api/v1/translations/languages/

    Returns list of available languages.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        languages = Language.objects.filter(is_active=True).values("code", "name")
        return success_response(list(languages))
