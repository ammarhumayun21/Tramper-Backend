"""
Shipment views for Tramper.
CRUD operations with custom permissions.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.parsers import NestedMultiPartParser, NestedFormParser

from .models import Shipment, ShipmentItem, Category
from .serializers import (
    ShipmentSerializer,
    ShipmentListSerializer,
    ShipmentCreateSerializer,
    ShipmentUpdateSerializer,
    ShipmentItemSerializer,
    CategorySerializer,
    MyShipmentListSerializer,
)
from .permissions import IsOwnerOrAdminOrReadOnly
from .filters import ShipmentFilter
from core.api import success_response


class MyShipmentsView(ListAPIView):
    """
    List current user's shipments (as sender or traveler).
    Includes is_accepted flag to indicate if there's an accepted request.
    """
    serializer_class = MyShipmentListSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ShipmentFilter
    search_fields = [
        "name",
        "notes",
        "from_location__city",
        "from_location__country",
        "to_location__city",
        "to_location__country",
        "items__name",
    ]
    ordering_fields = [
        "travel_date",
        "reward",
        "created_at",
        "updated_at",
        "status",
    ]

    def get_queryset(self):
        """Get shipments where user is sender or traveler."""
        from django.db.models import Q
        
        # Handle swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Shipment.objects.none()
        
        return Shipment.objects.select_related("sender", "traveler").prefetch_related(
            "items", "requests"
        ).filter(
            Q(sender=self.request.user) | Q(traveler=self.request.user)
        ).order_by("-created_at")

    @extend_schema(
        tags=["Shipments"],
        summary="Get my shipments",
        description="Get all shipments where the current user is sender or traveler with comprehensive filtering.",
        parameters=[
            # Status filter
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (pending, accepted, in_transit, delivered, cancelled)"),
            # Name filter
            OpenApiParameter("name", OpenApiTypes.STR, description="Filter by shipment name (partial match)"),
            # Location filters
            OpenApiParameter("from_location", OpenApiTypes.UUID, description="Filter by from location ID"),
            OpenApiParameter("to_location", OpenApiTypes.UUID, description="Filter by to location ID"),
            OpenApiParameter("from_city", OpenApiTypes.STR, description="Filter by from city (partial match)"),
            OpenApiParameter("to_city", OpenApiTypes.STR, description="Filter by to city (partial match)"),
            OpenApiParameter("from_country", OpenApiTypes.STR, description="Filter by from country (partial match)"),
            OpenApiParameter("to_country", OpenApiTypes.STR, description="Filter by to country (partial match)"),
            # Travel date filters
            OpenApiParameter("travel_date", OpenApiTypes.DATE, description="Filter by exact travel date"),
            OpenApiParameter("travel_date_from", OpenApiTypes.DATETIME, description="Filter by travel date (from)"),
            OpenApiParameter("travel_date_to", OpenApiTypes.DATETIME, description="Filter by travel date (to)"),
            # Reward filters
            OpenApiParameter("reward_min", OpenApiTypes.NUMBER, description="Filter by minimum reward amount"),
            OpenApiParameter("reward_max", OpenApiTypes.NUMBER, description="Filter by maximum reward amount"),
            # Item filters
            OpenApiParameter("has_items", OpenApiTypes.BOOL, description="Filter shipments that have items"),
            OpenApiParameter("item_category", OpenApiTypes.UUID, description="Filter by item category ID"),
            OpenApiParameter("item_category_name", OpenApiTypes.STR, description="Filter by item category name (partial match)"),
            # Date range filters
            OpenApiParameter("created_at_from", OpenApiTypes.DATETIME, description="Filter by created at (from)"),
            OpenApiParameter("created_at_to", OpenApiTypes.DATETIME, description="Filter by created at (to)"),
            # Search and ordering
            OpenApiParameter("search", OpenApiTypes.STR, description="Search in name, notes, locations, and items"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Order by field (prefix with - for descending)"),
        ],
        responses={
            200: OpenApiResponse(response=MyShipmentListSerializer(many=True), description="List of user's shipments"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ShipmentListCreateView(ListAPIView):
    """
    List all shipments or create a new shipment.
    GET: Anyone can list shipments (excluding current user's shipments)
    POST: Authenticated users can create shipments
    """
    serializer_class = ShipmentListSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    parser_classes = [NestedMultiPartParser, NestedFormParser, JSONParser]
    filterset_class = ShipmentFilter
    search_fields = [
        "name",
        "notes",
        "from_location__city",
        "from_location__country",
        "to_location__city",
        "to_location__country",
        "sender__username",
        "sender__full_name",
        "traveler__username",
        "traveler__full_name",
        "items__name",
    ]
    ordering_fields = [
        "travel_date",
        "reward",
        "created_at",
        "updated_at",
        "status",
        "name",
    ]

    def get_queryset(self):
        """Get all shipments excluding the current user's shipments."""
        from django.db.models import Q
        queryset = Shipment.objects.select_related("sender", "traveler").prefetch_related("items").all()
        
        # Exclude shipments where user is sender or traveler
        if self.request.user.is_authenticated:
            queryset = queryset.exclude(
                Q(sender=self.request.user) | Q(traveler=self.request.user)
            )
        
        return queryset.order_by("-created_at")

    @extend_schema(
        tags=["Shipments"],
        summary="List all shipments",
        description="Get a list of all shipments with comprehensive filtering and search capabilities.",
        parameters=[
            # Status filter
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (pending, accepted, in_transit, delivered, cancelled)"),
            # User filters
            OpenApiParameter("sender", OpenApiTypes.UUID, description="Filter by sender ID"),
            OpenApiParameter("sender_username", OpenApiTypes.STR, description="Filter by sender username (partial match)"),
            OpenApiParameter("traveler", OpenApiTypes.UUID, description="Filter by traveler ID"),
            OpenApiParameter("traveler_username", OpenApiTypes.STR, description="Filter by traveler username (partial match)"),
            OpenApiParameter("has_traveler", OpenApiTypes.BOOL, description="Filter shipments that have a traveler assigned"),
            # Name filter
            OpenApiParameter("name", OpenApiTypes.STR, description="Filter by shipment name (partial match)"),
            # Location filters
            OpenApiParameter("from_location", OpenApiTypes.UUID, description="Filter by from location ID"),
            OpenApiParameter("to_location", OpenApiTypes.UUID, description="Filter by to location ID"),
            OpenApiParameter("from_city", OpenApiTypes.STR, description="Filter by from city (partial match)"),
            OpenApiParameter("to_city", OpenApiTypes.STR, description="Filter by to city (partial match)"),
            OpenApiParameter("from_country", OpenApiTypes.STR, description="Filter by from country (partial match)"),
            OpenApiParameter("to_country", OpenApiTypes.STR, description="Filter by to country (partial match)"),
            # Travel date filters
            OpenApiParameter("travel_date", OpenApiTypes.DATE, description="Filter by exact travel date"),
            OpenApiParameter("travel_date_from", OpenApiTypes.DATETIME, description="Filter by travel date (from)"),
            OpenApiParameter("travel_date_to", OpenApiTypes.DATETIME, description="Filter by travel date (to)"),
            # Reward filters
            OpenApiParameter("reward", OpenApiTypes.NUMBER, description="Filter by exact reward amount"),
            OpenApiParameter("reward_min", OpenApiTypes.NUMBER, description="Filter by minimum reward amount"),
            OpenApiParameter("reward_max", OpenApiTypes.NUMBER, description="Filter by maximum reward amount"),
            # Item filters
            OpenApiParameter("has_items", OpenApiTypes.BOOL, description="Filter shipments that have items"),
            OpenApiParameter("item_category", OpenApiTypes.UUID, description="Filter by item category ID"),
            OpenApiParameter("item_category_name", OpenApiTypes.STR, description="Filter by item category name (partial match)"),
            # Date range filters
            OpenApiParameter("created_at_from", OpenApiTypes.DATETIME, description="Filter by created at (from)"),
            OpenApiParameter("created_at_to", OpenApiTypes.DATETIME, description="Filter by created at (to)"),
            OpenApiParameter("updated_at_from", OpenApiTypes.DATETIME, description="Filter by updated at (from)"),
            OpenApiParameter("updated_at_to", OpenApiTypes.DATETIME, description="Filter by updated at (to)"),
            # Search and ordering
            OpenApiParameter("search", OpenApiTypes.STR, description="Search in name, notes, locations, usernames, and items"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Order by field (prefix with - for descending)"),
        ],
        responses={
            200: OpenApiResponse(response=ShipmentListSerializer(many=True), description="List of shipments"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Shipments"],
        summary="Create a new shipment",
        description="Create a new shipment with items. Requires authentication.",
        request=ShipmentCreateSerializer,
        responses={
            201: OpenApiResponse(response=ShipmentSerializer, description="Shipment created successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = ShipmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipment = serializer.save(sender=request.user)
        return success_response(
            ShipmentSerializer(shipment).data,
            status_code=status.HTTP_201_CREATED,
        )


class ShipmentDetailView(APIView):
    """
    Retrieve, update, or delete a shipment.
    GET: Anyone can view
    PATCH: Owner or admin can update
    DELETE: Owner or admin can delete
    """
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    parser_classes = [NestedMultiPartParser, NestedFormParser, JSONParser]

    def get_object(self, pk):
        """Get shipment by ID."""
        try:
            shipment = Shipment.objects.select_related("sender", "traveler").prefetch_related(
                "items__dimensions"
            ).get(pk=pk)
            self.check_object_permissions(self.request, shipment)
            return shipment
        except Shipment.DoesNotExist:
            return None

    @extend_schema(
        tags=["Shipments"],
        summary="Get shipment details",
        description="Retrieve detailed information about a specific shipment.",
        responses={
            200: OpenApiResponse(response=ShipmentSerializer, description="Shipment details"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def get(self, request, pk):
        shipment = self.get_object(pk)
        if not shipment:
            return success_response(
                {"message": "Shipment not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = ShipmentSerializer(shipment)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Shipments"],
        summary="Update shipment",
        description="Update an existing shipment. Only owner or admin can update.",
        request=ShipmentUpdateSerializer,
        responses={
            200: OpenApiResponse(response=ShipmentSerializer, description="Shipment updated successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def patch(self, request, pk):
        shipment = self.get_object(pk)
        if not shipment:
            return success_response(
                {"message": "Shipment not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ShipmentUpdateSerializer(shipment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(ShipmentSerializer(shipment).data)

    @extend_schema(
        tags=["Shipments"],
        summary="Delete shipment",
        description="Delete a shipment. Only owner or admin can delete.",
        responses={
            200: OpenApiResponse(description="Shipment deleted successfully"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def delete(self, request, pk):
        shipment = self.get_object(pk)
        if not shipment:
            return success_response(
                {"message": "Shipment not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        shipment.delete()
        return success_response({"message": "Shipment deleted successfully"})


class ShipmentItemListCreateView(APIView):
    """
    List items for a shipment or add new items.
    GET: Anyone can view items
    POST: Owner or admin can add items
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [NestedMultiPartParser, NestedFormParser, JSONParser]

    def get_shipment(self, shipment_id):
        """Get shipment by ID."""
        try:
            return Shipment.objects.get(pk=shipment_id)
        except Shipment.DoesNotExist:
            return None

    @extend_schema(
        tags=["Shipment Items"],
        summary="List shipment items",
        description="Get all items for a specific shipment.",
        responses={
            200: OpenApiResponse(response=ShipmentItemSerializer(many=True), description="List of shipment items"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def get(self, request, shipment_id):
        shipment = self.get_shipment(shipment_id)
        if not shipment:
            return success_response(
                {"message": "Shipment not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        items = shipment.items.select_related("dimensions").all()
        serializer = ShipmentItemSerializer(items, many=True)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Shipment Items"],
        summary="Add item to shipment",
        description="Add a new item to an existing shipment. Only owner or admin can add items.",
        request=ShipmentItemSerializer,
        responses={
            201: OpenApiResponse(response=ShipmentItemSerializer, description="Item added successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment not found"),
        },
    )
    def post(self, request, shipment_id):
        shipment = self.get_shipment(shipment_id)
        if not shipment:
            return success_response(
                {"message": "Shipment not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check permissions
        if shipment.sender != request.user and not request.user.is_staff:
            return success_response(
                {"message": "Permission denied"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = ShipmentItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(shipment=shipment)
        return success_response(
            ShipmentItemSerializer(item).data,
            status_code=status.HTTP_201_CREATED,
        )


class ShipmentItemDetailView(APIView):
    """
    Retrieve, update, or delete a shipment item.
    GET: Anyone can view
    PATCH: Owner or admin can update
    DELETE: Owner or admin can delete
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [NestedMultiPartParser, NestedFormParser, JSONParser]

    def get_object(self, shipment_id, item_id):
        """Get shipment item by ID."""
        try:
            return ShipmentItem.objects.select_related("shipment", "dimensions").get(
                pk=item_id,
                shipment_id=shipment_id
            )
        except ShipmentItem.DoesNotExist:
            return None

    @extend_schema(
        tags=["Shipment Items"],
        summary="Get shipment item details",
        description="Retrieve detailed information about a specific shipment item.",
        responses={
            200: OpenApiResponse(response=ShipmentItemSerializer, description="Shipment item details"),
            404: OpenApiResponse(description="Shipment item not found"),
        },
    )
    def get(self, request, shipment_id, item_id):
        item = self.get_object(shipment_id, item_id)
        if not item:
            return success_response(
                {"message": "Shipment item not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ShipmentItemSerializer(item)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Shipment Items"],
        summary="Update shipment item",
        description="Update an existing shipment item. Only owner or admin can update.",
        request=ShipmentItemSerializer,
        responses={
            200: OpenApiResponse(response=ShipmentItemSerializer, description="Item updated successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment item not found"),
        },
    )
    def patch(self, request, shipment_id, item_id):
        item = self.get_object(shipment_id, item_id)
        if not item:
            return success_response(
                {"message": "Shipment item not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check permissions
        if item.shipment.sender != request.user and not request.user.is_staff:
            return success_response(
                {"message": "Permission denied"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = ShipmentItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(ShipmentItemSerializer(item).data)

    @extend_schema(
        tags=["Shipment Items"],
        summary="Delete shipment item",
        description="Delete a shipment item. Only owner or admin can delete.",
        responses={
            200: OpenApiResponse(description="Item deleted successfully"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment item not found"),
        },
    )
    def delete(self, request, shipment_id, item_id):
        item = self.get_object(shipment_id, item_id)
        if not item:
            return success_response(
                {"message": "Shipment item not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check permissions
        if item.shipment.sender != request.user and not request.user.is_staff:
            return success_response(
                {"message": "Permission denied"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        item.delete()
        return success_response({"message": "Shipment item deleted successfully"})


class ShipmentItemImageDeleteView(APIView):
    """
    Delete specific images from a shipment item.
    DELETE: Owner or admin can delete images
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, shipment_id, item_id):
        """Get shipment item by ID."""
        try:
            return ShipmentItem.objects.select_related("shipment").get(
                pk=item_id,
                shipment_id=shipment_id
            )
        except ShipmentItem.DoesNotExist:
            return None

    @extend_schema(
        tags=["Shipment Items"],
        summary="Delete image from shipment item",
        description="Delete a specific image from a shipment item by URL or index. Only owner or admin can delete.",
        parameters=[
            OpenApiParameter("url", OpenApiTypes.STR, description="The full S3 URL of the image to delete"),
            OpenApiParameter("index", OpenApiTypes.INT, description="The index of the image to delete (0-based)"),
        ],
        responses={
            200: OpenApiResponse(response=ShipmentItemSerializer, description="Image deleted successfully"),
            400: OpenApiResponse(description="URL or index required"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Shipment item or image not found"),
        },
    )
    def delete(self, request, shipment_id, item_id):
        item = self.get_object(shipment_id, item_id)
        if not item:
            return success_response(
                {"message": "Shipment item not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check permissions
        if item.shipment.sender != request.user and not request.user.is_staff:
            return success_response(
                {"message": "Permission denied"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        image_url = request.query_params.get("url")
        image_index = request.query_params.get("index")
        
        if not image_url and image_index is None:
            return success_response(
                {"message": "Either 'url' or 'index' query parameter is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        current_urls = item.image_urls or []
        
        if image_url:
            # Delete by URL
            if image_url not in current_urls:
                return success_response(
                    {"message": "Image not found in this item"},
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            
            # Delete from S3
            try:
                s3_storage.delete_image(image_url)
            except Exception as e:
                print(f"Failed to delete image from S3: {str(e)}")
            
            # Remove from list
            current_urls.remove(image_url)
        
        elif image_index is not None:
            # Delete by index
            try:
                index = int(image_index)
                if index < 0 or index >= len(current_urls):
                    return success_response(
                        {"message": "Image index out of range"},
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
                
                url_to_delete = current_urls[index]
                
                # Delete from S3
                try:
                    s3_storage.delete_image(url_to_delete)
                except Exception as e:
                    print(f"Failed to delete image from S3: {str(e)}")
                
                # Remove from list
                current_urls.pop(index)
            except ValueError:
                return success_response(
                    {"message": "Invalid index value"},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        
        # Save updated URLs
        item.image_urls = current_urls
        item.save(update_fields=['image_urls'])
        
        return success_response(ShipmentItemSerializer(item).data)


class CategoryListView(ListAPIView):
    """
    List all available categories for shipment items.
    GET: Anyone can view categories
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = []

    @extend_schema(
        tags=["Categories"],
        summary="List all categories",
        description="Get a list of all available categories for shipment items.",
        responses={
            200: OpenApiResponse(response=CategorySerializer(many=True), description="List of categories"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
