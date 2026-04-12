"""
Translation URL configuration.
"""

from django.urls import path
from .views import TranslationsView, LanguagesListView

urlpatterns = [
    path("", TranslationsView.as_view(), name="translations"),
    path("languages/", LanguagesListView.as_view(), name="languages_list"),
]
