"""
Core URL configuration.
Location, Airline, Country, and City API endpoints.
"""

from django.urls import path
from .views import (
    LocationListView,
    LocationCreateView,
    LocationDetailView,
    AirlineListView,
    CountryListView,
    CountryDetailView,
    CityListView,
)

urlpatterns = [
    path("", LocationListView.as_view(), name="location_list"),
    path("create/", LocationCreateView.as_view(), name="location_create"),
    path("<str:pk>/", LocationDetailView.as_view(), name="location_detail"),
]

# Airline URLs - will be included separately in main urls.py
airline_urlpatterns = [
    path("", AirlineListView.as_view(), name="airline_list"),
]

# Country URLs - will be included separately in main urls.py
country_urlpatterns = [
    path("", CountryListView.as_view(), name="country_list"),
    path("<str:pk>/", CountryDetailView.as_view(), name="country_detail"),
]

# City URLs - will be included separately in main urls.py
city_urlpatterns = [
    path("", CityListView.as_view(), name="city_list"),
]
