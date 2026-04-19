"""
Serializer mixins for common functionality.
"""

from rest_framework import serializers
from .models import Location, Airline, Country, City


class TimestampedSerializerMixin(serializers.Serializer):
    """
    Mixin that adds created_at and updated_at fields to serializers.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TranslatedChoiceField(serializers.ChoiceField):
    """
    Custom choice field that translates choices.
    """

    def __init__(self, choices, **kwargs):
        super().__init__(choices=choices, **kwargs)

    def to_representation(self, value):
        """Return choice value with display name."""
        if value is None:
            return None
        return {
            "value": value,
            "display": dict(self.choices).get(value, value),
        }


# ============================================================================
# COUNTRY SERIALIZERS
# ============================================================================


class CountrySerializer(serializers.ModelSerializer):
    """Full serializer for Country model."""

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "alpha_2",
            "alpha_3",
            "numeric_code",
            "region",
            "sub_region",
            "flag_emoji",
            "has_airports",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountryListSerializer(serializers.ModelSerializer):
    """Compact serializer for Country (used in nested responses)."""

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "alpha_2",
            "flag_emoji",
            "has_airports",
        ]
        read_only_fields = ["id"]


# ============================================================================
# CITY SERIALIZERS
# ============================================================================


class CitySerializer(serializers.ModelSerializer):
    """Full serializer for City model."""

    country = CountryListSerializer(read_only=True)

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "country",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CityListSerializer(serializers.ModelSerializer):
    """Compact serializer for City (used in lists and nested responses)."""

    country_name = serializers.CharField(source="country.name", read_only=True)
    country_alpha_2 = serializers.CharField(source="country.alpha_2", read_only=True)
    country_flag = serializers.CharField(source="country.flag_emoji", read_only=True)

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "country_name",
            "country_alpha_2",
            "country_flag",
        ]
        read_only_fields = ["id"]


# ============================================================================
# LOCATION (AIRPORT) SERIALIZERS
# ============================================================================


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model."""

    class Meta:
        model = Location
        fields = [
            "id",
            "country",
            "city",
            "airport_name",
            "iata_code",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LocationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Location (without read-only fields)."""

    class Meta:
        model = Location
        fields = ["country", "city", "airport_name", "iata_code"]


# ============================================================================
# AIRLINE SERIALIZERS
# ============================================================================


class AirlineSerializer(serializers.ModelSerializer):
    """Serializer for Airline model."""

    class Meta:
        model = Airline
        fields = [
            "id",
            "name",
            "iata_code",
            "country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
