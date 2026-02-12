"""
Core views for Tramper.
Location and Airline API endpoints.
"""

from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Location, Airline
from .serializers import LocationSerializer, LocationCreateSerializer, AirlineSerializer
from core.api import success_response


class LocationListView(ListAPIView):
    """
    List all locations or search by query.
    """
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]
    queryset = Location.objects.all()

    def get_queryset(self):
        """Filter locations by search query."""
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        
        if search:
            queryset = queryset.filter(
                models.Q(city__icontains=search) |
                models.Q(country__icontains=search) |
                models.Q(airport_name__icontains=search) |
                models.Q(iata_code__icontains=search)
            )
        
        return queryset.order_by("country", "city")

    @extend_schema(
        tags=["Locations"],
        summary="List locations",
        description="Get all locations or search by city, country, airport name, or IATA code.",
        parameters=[
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                description="Search query to filter locations",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=LocationSerializer(many=True),
                description="List of locations",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class LocationCreateView(APIView):
    """
    Create a new location.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Locations"],
        summary="Create a location",
        description="Create a new location entry.",
        request=LocationCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=LocationSerializer,
                description="Location created successfully",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = LocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if location already exists
        existing = Location.objects.filter(
            iata_code=serializer.validated_data.get("iata_code")
        ).first()
        
        if existing:
            return success_response(
                LocationSerializer(existing).data,
                status_code=status.HTTP_200_OK,
            )
        
        location = serializer.save()
        return success_response(
            LocationSerializer(location).data,
            status_code=status.HTTP_201_CREATED,
        )


class LocationDetailView(APIView):
    """
    Retrieve a location by ID or IATA code.
    """
    permission_classes = [AllowAny]

    def get_object(self, pk):
        """Get location by ID or IATA code."""
        # Try by UUID first
        try:
            return Location.objects.get(pk=pk)
        except (Location.DoesNotExist, ValueError):
            pass
        
        # Try by IATA code
        try:
            return Location.objects.get(iata_code__iexact=pk)
        except Location.DoesNotExist:
            return None

    @extend_schema(
        tags=["Locations"],
        summary="Get location details",
        description="Retrieve a location by ID or IATA code.",
        responses={
            200: OpenApiResponse(
                response=LocationSerializer,
                description="Location details",
            ),
            404: OpenApiResponse(description="Location not found"),
        },
    )
    def get(self, request, pk):
        location = self.get_object(pk)
        if not location:
            return success_response(
                {"message": "Location not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(LocationSerializer(location).data)


class AirlineListView(ListAPIView):
    """
    List all airlines or search by query.
    """
    serializer_class = AirlineSerializer
    permission_classes = [AllowAny]
    queryset = Airline.objects.all()

    def get_queryset(self):
        """Filter airlines by search query."""
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(iata_code__icontains=search) |
                models.Q(country__icontains=search)
            )
        
        return queryset.order_by("name")

    @extend_schema(
        tags=["Airlines"],
        summary="List airlines",
        description="Get all airlines or search by name, IATA code, or country.",
        parameters=[
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                description="Search query to filter airlines",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=AirlineSerializer(many=True),
                description="List of airlines",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
