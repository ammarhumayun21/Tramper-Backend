"""
Trip URLs for Tramper.
"""

from django.urls import path
from .views import TripListCreateView, TripDetailView, MyTripsView, MyDealsView, TripAcceptedRequestsView

urlpatterns = [
    path("", TripListCreateView.as_view(), name="trip_list_create"),
    path("my/", MyTripsView.as_view(), name="my_trips"),
    path("<uuid:pk>/", TripDetailView.as_view(), name="trip_detail"),
    path("<uuid:trip_id>/accepted-requests/", TripAcceptedRequestsView.as_view(), name="trip_accepted_requests"),
]
