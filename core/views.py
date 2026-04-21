"""
Core views for Tramper.
Location, Airline, Country, and City API endpoints.
"""

from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Location, Airline, Country, City
from .pagination import LargeResultsPagination
from .serializers import (
    LocationSerializer,
    LocationCreateSerializer,
    AirlineSerializer,
    CountrySerializer,
    CountryListSerializer,
    CitySerializer,
    CityListSerializer,
)
from core.api import success_response


# ============================================================================
# COUNTRY VIEWS
# ============================================================================


class CountryListView(ListAPIView):
    """
    List countries.

    By default, returns only countries that have airports in the database.
    Use ?show_all=true to return all 249 countries.
    """
    serializer_class = CountryListSerializer
    permission_classes = [AllowAny]
    pagination_class = LargeResultsPagination
    queryset = Country.objects.all()

    def get_queryset(self):
        """Filter countries by show_all flag and search query."""
        queryset = super().get_queryset()

        # show_all filter (default: False — only countries with airports)
        show_all = self.request.query_params.get("show_all", "").lower()
        if show_all not in ("true", "1", "yes"):
            queryset = queryset.filter(has_airports=True)

        # Search filter
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(alpha_2__iexact=search)
                | models.Q(alpha_3__iexact=search)
            )

        return queryset.order_by("name")

    @extend_schema(
        tags=["Countries"],
        summary="List countries",
        description=(
            "Get countries. By default only returns countries with airports. "
            "Use show_all=true to get all 249 countries."
        ),
        parameters=[
            OpenApiParameter(
                "show_all",
                OpenApiTypes.BOOL,
                description="If true, return all countries. Default: false (only countries with airports).",
            ),
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                description="Search by country name or ISO code.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CountryListSerializer(many=True),
                description="List of countries",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CountryDetailView(APIView):
    """
    Retrieve a country by ID or alpha-2 code.
    """
    permission_classes = [AllowAny]

    def get_object(self, pk):
        """Get country by UUID or alpha-2 code."""
        # Try by UUID first
        try:
            return Country.objects.get(pk=pk)
        except (Country.DoesNotExist, ValueError):
            pass

        # Try by alpha-2 code
        try:
            return Country.objects.get(alpha_2__iexact=pk)
        except Country.DoesNotExist:
            pass

        # Try by alpha-3 code
        try:
            return Country.objects.get(alpha_3__iexact=pk)
        except Country.DoesNotExist:
            return None

    @extend_schema(
        tags=["Countries"],
        summary="Get country details",
        description="Retrieve a country by ID, alpha-2 code (US), or alpha-3 code (USA).",
        responses={
            200: OpenApiResponse(
                response=CountrySerializer,
                description="Country details",
            ),
            404: OpenApiResponse(description="Country not found"),
        },
    )
    def get(self, request, pk):
        country = self.get_object(pk)
        if not country:
            return success_response(
                {"message": "Country not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(CountrySerializer(country).data)


# ============================================================================
# CITY VIEWS
# ============================================================================


class CityListView(ListAPIView):
    """
    List cities, optionally filtered by country.
    """
    serializer_class = CityListSerializer
    permission_classes = [AllowAny]
    pagination_class = LargeResultsPagination
    queryset = City.objects.select_related("country").all()

    def get_queryset(self):
        """Filter cities by country and search query."""
        queryset = super().get_queryset()

        # Country filter (alpha-2 code)
        country = self.request.query_params.get("country", "").strip()
        if country:
            queryset = queryset.filter(country__alpha_2__iexact=country)

        # Search filter
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(country__name__icontains=search)
            )

        return queryset.order_by("country__name", "name")

    @extend_schema(
        tags=["Cities"],
        summary="List cities",
        description="Get cities, optionally filtered by country alpha-2 code.",
        parameters=[
            OpenApiParameter(
                "country",
                OpenApiTypes.STR,
                description="Filter by country alpha-2 code (e.g., US, GB, AE).",
            ),
            OpenApiParameter(
                "search",
                OpenApiTypes.STR,
                description="Search by city name or country name.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=CityListSerializer(many=True),
                description="List of cities",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ============================================================================
# LOCATION (AIRPORT) VIEWS
# ============================================================================


class LocationListView(ListAPIView):
    """
    List all locations or search by query.
    """
    serializer_class = LocationSerializer
    permission_classes = [AllowAny]
    pagination_class = LargeResultsPagination
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


# ============================================================================
# AIRLINE VIEWS
# ============================================================================


class AirlineListView(ListAPIView):
    """
    List all airlines or search by query.
    """
    serializer_class = AirlineSerializer
    permission_classes = [AllowAny]
    pagination_class = LargeResultsPagination
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
