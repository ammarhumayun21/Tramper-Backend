"""
Shipment filters for Tramper.
Comprehensive filtering for shipment list endpoints.
"""

import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Shipment


class ShipmentFilter(django_filters.FilterSet):
    """
    Comprehensive filter for Shipment model.
    Supports filtering on all relevant fields.
    """

    # Status filter
    status = django_filters.ChoiceFilter(
        choices=Shipment.STATUS_CHOICES,
        help_text=_("Filter by shipment status"),
    )

    # User filters
    sender = django_filters.UUIDFilter(
        field_name="sender__id",
        help_text=_("Filter by sender ID"),
    )
    sender_username = django_filters.CharFilter(
        field_name="sender__username",
        lookup_expr="icontains",
        help_text=_("Filter by sender username (partial match)"),
    )
    traveler = django_filters.UUIDFilter(
        field_name="traveler__id",
        help_text=_("Filter by traveler ID"),
    )
    traveler_username = django_filters.CharFilter(
        field_name="traveler__username",
        lookup_expr="icontains",
        help_text=_("Filter by traveler username (partial match)"),
    )
    has_traveler = django_filters.BooleanFilter(
        field_name="traveler",
        lookup_expr="isnull",
        exclude=True,
        help_text=_("Filter shipments that have a traveler assigned"),
    )

    # Name filter
    name = django_filters.CharFilter(
        lookup_expr="icontains",
        help_text=_("Filter by shipment name (partial match)"),
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

    # Travel date filters
    travel_date = django_filters.DateFilter(
        field_name="travel_date",
        lookup_expr="date",
        help_text=_("Filter by exact travel date"),
    )
    travel_date_from = django_filters.DateTimeFilter(
        field_name="travel_date",
        lookup_expr="gte",
        help_text=_("Filter by travel date (from)"),
    )
    travel_date_to = django_filters.DateTimeFilter(
        field_name="travel_date",
        lookup_expr="lte",
        help_text=_("Filter by travel date (to)"),
    )

    # Reward filters
    reward = django_filters.NumberFilter(
        help_text=_("Filter by exact reward amount"),
    )
    reward_min = django_filters.NumberFilter(
        field_name="reward",
        lookup_expr="gte",
        help_text=_("Filter by minimum reward amount"),
    )
    reward_max = django_filters.NumberFilter(
        field_name="reward",
        lookup_expr="lte",
        help_text=_("Filter by maximum reward amount"),
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

    # Item-related filters
    has_items = django_filters.BooleanFilter(
        method="filter_has_items",
        help_text=_("Filter shipments that have items"),
    )
    item_category = django_filters.UUIDFilter(
        field_name="items__category__id",
        help_text=_("Filter by item category ID"),
    )
    item_category_name = django_filters.CharFilter(
        field_name="items__category__name",
        lookup_expr="icontains",
        help_text=_("Filter by item category name (partial match)"),
    )

    # Search filter for multiple fields
    search = django_filters.CharFilter(
        method="filter_search",
        help_text=_("Search in name, notes, locations, and usernames"),
    )

    class Meta:
        model = Shipment
        fields = [
            "status",
            "sender",
            "sender_username",
            "traveler",
            "traveler_username",
            "has_traveler",
            "name",
            "from_location",
            "to_location",
            "from_city",
            "to_city",
            "from_country",
            "to_country",
            "travel_date",
            "travel_date_from",
            "travel_date_to",
            "reward",
            "reward_min",
            "reward_max",
            "created_at_from",
            "created_at_to",
            "updated_at_from",
            "updated_at_to",
            "has_items",
            "item_category",
            "item_category_name",
            "search",
        ]

    def filter_has_items(self, queryset, name, value):
        """Filter shipments based on whether they have items."""
        if value is True:
            return queryset.filter(items__isnull=False).distinct()
        elif value is False:
            return queryset.filter(items__isnull=True)
        return queryset

    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if value:
            return queryset.filter(
                Q(name__icontains=value)
                | Q(notes__icontains=value)
                | Q(from_location__city__icontains=value)
                | Q(from_location__country__icontains=value)
                | Q(to_location__city__icontains=value)
                | Q(to_location__country__icontains=value)
                | Q(sender__username__icontains=value)
                | Q(sender__full_name__icontains=value)
                | Q(traveler__username__icontains=value)
                | Q(traveler__full_name__icontains=value)
                | Q(items__name__icontains=value)
            ).distinct()
        return queryset
