"""
URL configuration for shipments app.
"""

from django.urls import path
from .views import (
    MyShipmentsView,
    ShipmentListCreateView,
    ShipmentDetailView,
    ShipmentItemListCreateView,
    ShipmentItemDetailView,
    ShipmentItemImageDeleteView,
)

app_name = "shipments"

urlpatterns = [
    # My shipments endpoint (must be before <uuid:pk>)
    path("my/", MyShipmentsView.as_view(), name="my-shipments"),
    
    # Shipment endpoints
    path("", ShipmentListCreateView.as_view(), name="shipment-list-create"),
    path("<uuid:pk>/", ShipmentDetailView.as_view(), name="shipment-detail"),
    
    # Shipment item endpoints
    path("<uuid:shipment_id>/items/", ShipmentItemListCreateView.as_view(), name="shipment-item-list-create"),
    path("<uuid:shipment_id>/items/<uuid:item_id>/", ShipmentItemDetailView.as_view(), name="shipment-item-detail"),
    path("<uuid:shipment_id>/items/<uuid:item_id>/images/", ShipmentItemImageDeleteView.as_view(), name="shipment-item-image-delete"),
]
