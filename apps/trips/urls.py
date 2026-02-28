"""
Trip URLs for Tramper.
"""

from django.urls import path
from .views import TripListCreateView, TripDetailView, MyTripsView, MyDealsView

urlpatterns = [
    path("", TripListCreateView.as_view(), name="trip_list_create"),
    path("my/", MyTripsView.as_view(), name="my_trips"),
    path("my-deals/", MyDealsView.as_view(), name="my_deals"),
    path("<uuid:pk>/", TripDetailView.as_view(), name="trip_detail"),
]
