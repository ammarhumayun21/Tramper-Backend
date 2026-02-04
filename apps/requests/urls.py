"""
URL configuration for requests app.
"""

from django.urls import path
from .views import (
    MyRequestsView,
    RequestListCreateView,
    RequestDetailView,
    CounterOfferCreateView,
    ShipmentRequestsView,
    TripRequestsView,
)

app_name = "requests"

urlpatterns = [
    # My requests
    path("my/", MyRequestsView.as_view(), name="my-requests"),
    
    # Request CRUD
    path("", RequestListCreateView.as_view(), name="request-create"),
    path("<uuid:pk>/", RequestDetailView.as_view(), name="request-detail"),
    
    # Counter offers
    path("<uuid:pk>/counter/", CounterOfferCreateView.as_view(), name="counter-offer-create"),
    
    # Requests by shipment/trip
    path("shipment/<uuid:shipment_id>/", ShipmentRequestsView.as_view(), name="shipment-requests"),
    path("trip/<uuid:trip_id>/", TripRequestsView.as_view(), name="trip-requests"),
]
