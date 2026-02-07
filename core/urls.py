"""
Core URL configuration.
Location API endpoints.
"""

from django.urls import path
from .views import LocationListView, LocationCreateView, LocationDetailView

urlpatterns = [
    path("", LocationListView.as_view(), name="location_list"),
    path("create/", LocationCreateView.as_view(), name="location_create"),
    path("<str:pk>/", LocationDetailView.as_view(), name="location_detail"),
]
