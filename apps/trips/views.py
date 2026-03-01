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
from .filters import TripFilter
from core.api import success_response
from apps.requests.models import Request
from apps.requests.serializers import RequestSerializer


class TripListCreateView(ListAPIView):
    """
    List all trips or create a new trip.
    GET: Anyone can list trips (excluding current user's trips)
    POST: Authenticated users can create trips
    """
    serializer_class = TripListSerializer
    permission_classes = [IsOwnerOrAdminOrReadOnly]
    filterset_class = TripFilter
    search_fields = [
        "first_name",
        "last_name",
        "from_location__city",
        "from_location__country",
        "to_location__city",
        "to_location__country",
        "traveler__username",
        "traveler__full_name",
        "notes",
        "booking_reference",
    ]
    ordering_fields = [
        "departure_date",
        "departure_time",
        "created_at",
        "updated_at",
        "capacity__total_weight",
        "capacity__available_weight",
    ]

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
        description="Get a list of all trips with comprehensive filtering and search capabilities.",
        parameters=[
            # Status and mode filters
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (valid, invalid)"),
            OpenApiParameter("mode", OpenApiTypes.STR, description="Filter by mode of transport (trip, train, ship, bus)"),
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by preferred category"),
            # Traveler filters
            OpenApiParameter("traveler", OpenApiTypes.UUID, description="Filter by traveler ID"),
            OpenApiParameter("traveler_username", OpenApiTypes.STR, description="Filter by traveler username (partial match)"),
            # Name filters
            OpenApiParameter("first_name", OpenApiTypes.STR, description="Filter by first name (partial match)"),
            OpenApiParameter("last_name", OpenApiTypes.STR, description="Filter by last name (partial match)"),
            # Location filters
            OpenApiParameter("from_location", OpenApiTypes.UUID, description="Filter by from location ID"),
            OpenApiParameter("to_location", OpenApiTypes.UUID, description="Filter by to location ID"),
            OpenApiParameter("from_city", OpenApiTypes.STR, description="Filter by from city (partial match)"),
            OpenApiParameter("to_city", OpenApiTypes.STR, description="Filter by to city (partial match)"),
            OpenApiParameter("from_country", OpenApiTypes.STR, description="Filter by from country (partial match)"),
            OpenApiParameter("to_country", OpenApiTypes.STR, description="Filter by to country (partial match)"),
            # Airline filters
            OpenApiParameter("airline", OpenApiTypes.UUID, description="Filter by airline ID"),
            OpenApiParameter("airline_name", OpenApiTypes.STR, description="Filter by airline name (partial match)"),
            # Date filters
            OpenApiParameter("departure_date", OpenApiTypes.DATE, description="Filter by exact departure date"),
            OpenApiParameter("departure_date_from", OpenApiTypes.DATE, description="Filter by departure date (from)"),
            OpenApiParameter("departure_date_to", OpenApiTypes.DATE, description="Filter by departure date (to)"),
            OpenApiParameter("pickup_availability_start_date_from", OpenApiTypes.DATE, description="Filter by pickup start date (from)"),
            OpenApiParameter("pickup_availability_start_date_to", OpenApiTypes.DATE, description="Filter by pickup start date (to)"),
            OpenApiParameter("pickup_availability_end_date_from", OpenApiTypes.DATE, description="Filter by pickup end date (from)"),
            OpenApiParameter("pickup_availability_end_date_to", OpenApiTypes.DATE, description="Filter by pickup end date (to)"),
            # Capacity filters
            OpenApiParameter("min_available_weight", OpenApiTypes.NUMBER, description="Filter trips with at least this available weight"),
            OpenApiParameter("max_used_weight", OpenApiTypes.NUMBER, description="Filter by maximum used weight"),
            OpenApiParameter("capacity_unit", OpenApiTypes.STR, description="Filter by capacity unit (e.g., kg, lbs)"),
            # Booking reference
            OpenApiParameter("booking_reference", OpenApiTypes.STR, description="Filter by booking reference (partial match)"),
            # Date range filters
            OpenApiParameter("created_at_from", OpenApiTypes.DATETIME, description="Filter by created at (from)"),
            OpenApiParameter("created_at_to", OpenApiTypes.DATETIME, description="Filter by created at (to)"),
            OpenApiParameter("updated_at_from", OpenApiTypes.DATETIME, description="Filter by updated at (from)"),
            OpenApiParameter("updated_at_to", OpenApiTypes.DATETIME, description="Filter by updated at (to)"),
            # Search
            OpenApiParameter("search", OpenApiTypes.STR, description="Search in names, locations, notes, and booking reference"),
            # Ordering
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Order by field (prefix with - for descending)"),
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
    filterset_class = TripFilter
    search_fields = [
        "first_name",
        "last_name",
        "from_location__city",
        "from_location__country",
        "to_location__city",
        "to_location__country",
        "notes",
        "booking_reference",
    ]
    ordering_fields = [
        "departure_date",
        "departure_time",
        "created_at",
        "updated_at",
        "capacity__total_weight",
    ]

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
        description="Get all trips created by the authenticated user with comprehensive filtering and search capabilities.",
        parameters=[
            # Status and mode filters
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (valid, invalid)"),
            OpenApiParameter("mode", OpenApiTypes.STR, description="Filter by mode of transport (trip, train, ship, bus)"),
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by preferred category"),
            # Name filters
            OpenApiParameter("first_name", OpenApiTypes.STR, description="Filter by first name (partial match)"),
            OpenApiParameter("last_name", OpenApiTypes.STR, description="Filter by last name (partial match)"),
            # Location filters
            OpenApiParameter("from_location", OpenApiTypes.UUID, description="Filter by from location ID"),
            OpenApiParameter("to_location", OpenApiTypes.UUID, description="Filter by to location ID"),
            OpenApiParameter("from_city", OpenApiTypes.STR, description="Filter by from city (partial match)"),
            OpenApiParameter("to_city", OpenApiTypes.STR, description="Filter by to city (partial match)"),
            OpenApiParameter("from_country", OpenApiTypes.STR, description="Filter by from country (partial match)"),
            OpenApiParameter("to_country", OpenApiTypes.STR, description="Filter by to country (partial match)"),
            # Airline filters
            OpenApiParameter("airline", OpenApiTypes.UUID, description="Filter by airline ID"),
            OpenApiParameter("airline_name", OpenApiTypes.STR, description="Filter by airline name (partial match)"),
            # Date filters
            OpenApiParameter("departure_date", OpenApiTypes.DATE, description="Filter by exact departure date"),
            OpenApiParameter("departure_date_from", OpenApiTypes.DATE, description="Filter by departure date (from)"),
            OpenApiParameter("departure_date_to", OpenApiTypes.DATE, description="Filter by departure date (to)"),
            # Capacity filters
            OpenApiParameter("min_available_weight", OpenApiTypes.NUMBER, description="Filter trips with at least this available weight"),
            OpenApiParameter("capacity_unit", OpenApiTypes.STR, description="Filter by capacity unit (e.g., kg, lbs)"),
            # Booking reference
            OpenApiParameter("booking_reference", OpenApiTypes.STR, description="Filter by booking reference (partial match)"),
            # Date range filters
            OpenApiParameter("created_at_from", OpenApiTypes.DATETIME, description="Filter by created at (from)"),
            OpenApiParameter("created_at_to", OpenApiTypes.DATETIME, description="Filter by created at (to)"),
            # Search and ordering
            OpenApiParameter("search", OpenApiTypes.STR, description="Search in names, locations, notes, and booking reference"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="Order by field (prefix with - for descending)"),
        ],
        responses={
            200: OpenApiResponse(response=MyTripListSerializer(many=True), description="User's trips with requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyDealsView(ListAPIView):
    """
    Get all trips where at least one request has been accepted.
    Includes is_accepted flag and accepted requests with shipments.
    """
    serializer_class = MyTripListSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TripFilter
    search_fields = [
        "first_name",
        "last_name",
        "from_location__city",
        "from_location__country",
        "to_location__city",
        "to_location__country",
        "notes",
        "booking_reference",
    ]
    ordering_fields = [
        "departure_date",
        "departure_time",
        "created_at",
        "updated_at",
        "capacity__total_weight",
    ]

    def get_queryset(self):
        # Handle swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Trip.objects.none()
        
        # Filter for trips where user is traveler AND has at least one accepted request
        return Trip.objects.select_related("capacity", "traveler").prefetch_related(
            "requests", "requests__shipment", "requests__shipment__items"
        ).filter(
            traveler=self.request.user,
            requests__status="accepted"
        ).distinct().order_by("-created_at")

    @extend_schema(
        tags=["Trips"],
        summary="Get my deals",
        description="Get all trips created by the authenticated user that have at least one accepted request.",
        responses={
            200: OpenApiResponse(response=MyTripListSerializer(many=True), description="User's trips with accepted requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TripAcceptedRequestsView(APIView):
    """
    Returns all accepted requests for a given trip.
    Pass the trip ID and get back only the requests with status='accepted'.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Trips"],
        summary="Get accepted requests for a trip",
        description="Returns all requests with status 'accepted' for the specified trip.",
        responses={
            200: OpenApiResponse(response=RequestSerializer(many=True), description="List of accepted requests"),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    def get(self, request, trip_id):
        # Verify the trip exists
        if not Trip.objects.filter(pk=trip_id).exists():
            return success_response(
                {"message": "Trip not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        accepted_requests = (
            Request.objects.filter(trip_id=trip_id, status="accepted")
            .select_related("sender", "receiver", "shipment", "trip")
            .prefetch_related(
                "counter_offers",
                "shipment__items",
            )
            .order_by("-created_at")
        )

        serializer = RequestSerializer(
            accepted_requests,
            many=True,
            context={"request": request},
        )
        return success_response(serializer.data)
