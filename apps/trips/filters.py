"""
Trip filters for Tramper.
Comprehensive filtering for trip list endpoints.
"""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Trip


class TripFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Trip model.
    Supports filtering on all relevant fields.
    """

    # Status and mode filters
    status = django_filters.ChoiceFilter(
        choices=Trip.STATUS_CHOICES,
        help_text=_("Filter by trip status"),
    )
    mode = django_filters.ChoiceFilter(
        choices=Trip.MODE_CHOICES,
        help_text=_("Filter by mode of transport"),
    )
    category = django_filters.ChoiceFilter(
        choices=Trip.CATEGORY_CHOICES,
        help_text=_("Filter by preferred category"),
    )

    # Traveler filters
    traveler = django_filters.UUIDFilter(
        field_name="traveler__id",
        help_text=_("Filter by traveler ID"),
    )
    traveler_username = django_filters.CharFilter(
        field_name="traveler__username",
        lookup_expr="icontains",
        help_text=_("Filter by traveler username (partial match)"),
    )

    # Name filters
    first_name = django_filters.CharFilter(
        lookup_expr="icontains",
        help_text=_("Filter by first name (partial match)"),
    )
    last_name = django_filters.CharFilter(
        lookup_expr="icontains",
        help_text=_("Filter by last name (partial match)"),
    )

    # Location filters
    from_location = django_filters.UUIDFilter(
        field_name="from_location__id",
        help_text=_("Filter by from location ID"),
    )
    to_location = django_filters.UUIDFilter(
        field_name="to_location__id",
        help_text=_("Filter by to location ID"),
    )
    from_city = django_filters.CharFilter(
        field_name="from_location__city",
        lookup_expr="icontains",
        help_text=_("Filter by from city (partial match)"),
    )
    to_city = django_filters.CharFilter(
        field_name="to_location__city",
        lookup_expr="icontains",
        help_text=_("Filter by to city (partial match)"),
    )
    from_country = django_filters.CharFilter(
        field_name="from_location__country",
        lookup_expr="icontains",
        help_text=_("Filter by from country (partial match)"),
    )
    to_country = django_filters.CharFilter(
        field_name="to_location__country",
        lookup_expr="icontains",
        help_text=_("Filter by to country (partial match)"),
    )

    # Airline filter
    airline = django_filters.UUIDFilter(
        field_name="airline__id",
        help_text=_("Filter by airline ID"),
    )
    airline_name = django_filters.CharFilter(
        field_name="airline__name",
        lookup_expr="icontains",
        help_text=_("Filter by airline name (partial match)"),
    )

    # Date filters
    departure_date = django_filters.DateFilter(
        help_text=_("Filter by exact departure date"),
    )
    departure_date_from = django_filters.DateFilter(
        field_name="departure_date",
        lookup_expr="gte",
        help_text=_("Filter by departure date (from)"),
    )
    departure_date_to = django_filters.DateFilter(
        field_name="departure_date",
        lookup_expr="lte",
        help_text=_("Filter by departure date (to)"),
    )

    # Pickup availability date filters
    pickup_availability_start_date_from = django_filters.DateFilter(
        field_name="pickup_availability_start_date",
        lookup_expr="gte",
        help_text=_("Filter by pickup availability start date (from)"),
    )
    pickup_availability_start_date_to = django_filters.DateFilter(
        field_name="pickup_availability_start_date",
        lookup_expr="lte",
        help_text=_("Filter by pickup availability start date (to)"),
    )
    pickup_availability_end_date_from = django_filters.DateFilter(
        field_name="pickup_availability_end_date",
        lookup_expr="gte",
        help_text=_("Filter by pickup availability end date (from)"),
    )
    pickup_availability_end_date_to = django_filters.DateFilter(
        field_name="pickup_availability_end_date",
        lookup_expr="lte",
        help_text=_("Filter by pickup availability end date (to)"),
    )

    # Capacity filters
    min_available_weight = django_filters.NumberFilter(
        method="filter_min_available_weight",
        help_text=_("Filter trips with at least this available weight"),
    )
    max_used_weight = django_filters.NumberFilter(
        field_name="capacity__used_weight",
        lookup_expr="lte",
        help_text=_("Filter by maximum used weight"),
    )
    capacity_unit = django_filters.CharFilter(
        field_name="capacity__unit",
        lookup_expr="iexact",
        help_text=_("Filter by capacity unit (e.g., kg, lbs)"),
    )

    # Created/Updated date filters
    created_at_from = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text=_("Filter by created at (from)"),
    )
    created_at_to = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text=_("Filter by created at (to)"),
    )
    updated_at_from = django_filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="gte",
        help_text=_("Filter by updated at (from)"),
    )
    updated_at_to = django_filters.DateTimeFilter(
        field_name="updated_at",
        lookup_expr="lte",
        help_text=_("Filter by updated at (to)"),
    )

    # Booking reference
    booking_reference = django_filters.CharFilter(
        lookup_expr="icontains",
        help_text=_("Filter by booking reference (partial match)"),
    )

    # Search filter for multiple fields
    search = django_filters.CharFilter(
        method="filter_search",
        help_text=_("Search in first name, last name, locations, and notes"),
    )

    class Meta:
        model = Trip
        fields = [
            "status",
            "mode",
            "category",
            "traveler",
            "traveler_username",
            "first_name",
            "last_name",
            "from_location",
            "to_location",
            "from_city",
            "to_city",
            "from_country",
            "to_country",
            "airline",
            "airline_name",
            "departure_date",
            "departure_date_from",
            "departure_date_to",
            "pickup_availability_start_date_from",
            "pickup_availability_start_date_to",
            "pickup_availability_end_date_from",
            "pickup_availability_end_date_to",
            "min_available_weight",
            "max_used_weight",
            "capacity_unit",
            "created_at_from",
            "created_at_to",
            "updated_at_from",
            "updated_at_to",
            "booking_reference",
            "search",
        ]

    def filter_min_available_weight(self, queryset, name, value):
        """Filter trips with at least the specified available weight."""
        if value is not None:
            from django.db.models import F
            return queryset.annotate(
                available=F("capacity__total_weight") - F("capacity__used_weight")
            ).filter(available__gte=value)
        return queryset

    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if value:
            return queryset.filter(
                Q(first_name__icontains=value)
                | Q(last_name__icontains=value)
                | Q(from_location__city__icontains=value)
                | Q(from_location__country__icontains=value)
                | Q(to_location__city__icontains=value)
                | Q(to_location__country__icontains=value)
                | Q(notes__icontains=value)
                | Q(booking_reference__icontains=value)
                | Q(traveler__username__icontains=value)
                | Q(traveler__full_name__icontains=value)
            )
        return queryset
