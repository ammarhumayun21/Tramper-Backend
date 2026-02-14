"""
Trip views for Tramper.
CRUD operations with custom permissions.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Trip
from .serializers import TripSerializer, TripListSerializer, MyTripListSerializer
from .permissions import IsOwnerOrAdminOrReadOnly
from core.api import success_response


class TripListCreateView(ListAPIView):
    """
    List all trips or create a new trip.
    GET: Anyone can list trips (excluding current user's trips)
    POST: Authenticated users can create trips
    """
    serializer_class = TripListSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    filterset_fields = ["status", "mode", "category"]
    search_fields = ["from_location", "to_location", "first_name", "last_name"]
    ordering_fields = ["departure_date", "departure_time", "created_at"]

    def get_queryset(self):
        """Get all trips excluding the current user's trips."""
        queryset = Trip.objects.select_related("capacity", "traveler").all()
        
        # Exclude trips where user is the traveler
        if self.request.user.is_authenticated:
            queryset = queryset.exclude(traveler=self.request.user)
        
        return queryset.order_by("-created_at")

    @extend_schema(
        tags=["Trips"],
        summary="List all trips",
        description="Get a list of all trips with filtering and search capabilities.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status"),
            OpenApiParameter("mode", OpenApiTypes.STR, description="Filter by mode of transport"),
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by category"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search in locations and names"),
        ],
        responses={
            200: OpenApiResponse(response=TripListSerializer(many=True), description="List of trips"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Trips"],
        summary="Create a new trip",
        description="Create a new trip. Requires authentication.",
        request=TripSerializer,
        responses={
            201: OpenApiResponse(response=TripSerializer, description="Trip created successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = TripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save(traveler=request.user)
        return success_response(
            TripSerializer(trip).data,
            status_code=status.HTTP_201_CREATED,
        )


class TripDetailView(APIView):
    """
    Retrieve, update, or delete a trip.
    GET: Anyone can view
    PATCH: Owner or admin can update
    DELETE: Owner or admin can delete
    """
    permission_classes = [IsOwnerOrAdminOrReadOnly]

    def get_object(self, pk):
        """Get trip by ID."""
        try:
            trip = Trip.objects.select_related("capacity", "traveler").get(pk=pk)
            self.check_object_permissions(self.request, trip)
            return trip
        except Trip.DoesNotExist:
            return None

    @extend_schema(
        tags=["Trips"],
        summary="Get trip details",
        description="Retrieve detailed information about a specific trip.",
        responses={
            200: OpenApiResponse(response=TripSerializer, description="Trip details"),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    def get(self, request, pk):
        trip = self.get_object(pk)
        if not trip:
            return success_response(
                {"message": "Trip not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = TripSerializer(trip)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Trips"],
        summary="Update trip",
        description="Update a trip. Only owner or admin can update.",
        request=TripSerializer,
        responses={
            200: OpenApiResponse(response=TripSerializer, description="Trip updated successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    def patch(self, request, pk):
        trip = self.get_object(pk)
        if not trip:
            return success_response(
                {"message": "Trip not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = TripSerializer(trip, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data)

    @extend_schema(
        tags=["Trips"],
        summary="Delete trip",
        description="Delete a trip. Only owner or admin can delete.",
        responses={
            200: OpenApiResponse(description="Trip deleted successfully"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    def delete(self, request, pk):
        trip = self.get_object(pk)
        if not trip:
            return success_response(
                {"message": "Trip not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        trip.delete()
        return success_response({"message": "Trip deleted successfully"})


class MyTripsView(ListAPIView):
    """
    Get all trips created by the authenticated user.
    Includes is_accepted flag and accepted requests with shipments.
    """
    serializer_class = MyTripListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Handle swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Trip.objects.none()
        
        return Trip.objects.select_related("capacity", "traveler").prefetch_related(
            "requests", "requests__shipment", "requests__shipment__items"
        ).filter(
            traveler=self.request.user
        ).order_by("-created_at")

    @extend_schema(
        tags=["Trips"],
        summary="Get my trips",
        description="Get all trips created by the authenticated user with accepted requests and shipments.",
        responses={
            200: OpenApiResponse(response=MyTripListSerializer(many=True), description="User's trips with requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

