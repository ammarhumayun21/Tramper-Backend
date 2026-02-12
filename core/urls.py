"""
Core URL configuration.
Location and Airline API endpoints.
"""

from django.urls import path
from .views import LocationListView, LocationCreateView, LocationDetailView, AirlineListView

urlpatterns = [
    path("", LocationListView.as_view(), name="location_list"),
    path("create/", LocationCreateView.as_view(), name="location_create"),
    path("<str:pk>/", LocationDetailView.as_view(), name="location_detail"),
]

# Airline URLs - will be included separately in main urls.py
airline_urlpatterns = [
    path("", AirlineListView.as_view(), name="airline_list"),
]
