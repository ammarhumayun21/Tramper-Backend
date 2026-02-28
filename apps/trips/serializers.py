"""
Trip serializers for Tramper.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Trip, TripCapacity
from core.serializers import LocationSerializer, AirlineSerializer
from core.models import Location, Airline
from apps.users.models import User


class UserSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for user summary in trips."""

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "profile_image_url",
            "rating",
            "total_trips",
            "total_deals",
            "total_shipments",
        ]
        read_only_fields = fields


class TripCapacitySerializer(serializers.ModelSerializer):
    """Serializer for trip capacity."""

    available_weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    is_full = serializers.BooleanField(read_only=True)

    class Meta:
        model = TripCapacity
        fields = [
            "id",
            "total_weight",
            "used_weight",
            "available_weight",
            "is_full",
            "unit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TripSerializer(serializers.ModelSerializer):
    """Serializer for trip data."""

    capacity = TripCapacitySerializer()
    traveler_id = serializers.UUIDField(source="traveler.id", read_only=True)
    traveler = UserSummarySerializer(read_only=True)
    is_accepted = serializers.SerializerMethodField()
    from_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    airline = serializers.PrimaryKeyRelatedField(
        queryset=Airline.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Trip
        fields = [
            "id",
            "traveler_id",
            "traveler",
            "first_name",
            "last_name",
            "mode",
            "status",
            "from_location",
            "to_location",
            "departure_date",
            "departure_time",
            "capacity",
            "transport_details",
            "category",
            "notes",
            "airline",
            "pickup_availability_start_date",
            "pickup_availability_end_date",
            "meeting_points",
            "is_accepted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "traveler_id", "traveler", "is_accepted", "created_at", "updated_at"]

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_accepted(self, obj) -> bool:
        """Check if the trip has any accepted requests."""
        if not obj.pk:
            return False
        return obj.requests.filter(status="accepted").exists()

    def to_representation(self, instance):
        """Return complete location and airline objects in response."""
        data = super().to_representation(instance)
        # Replace location UUIDs with full objects
        if instance.from_location:
            data['from_location'] = LocationSerializer(instance.from_location).data
        if instance.to_location:
            data['to_location'] = LocationSerializer(instance.to_location).data
        # Replace airline UUID with full object
        if instance.airline:
            data['airline'] = AirlineSerializer(instance.airline).data
        return data

    def validate_departure_time(self, value):
        """Handle both time and datetime strings for departure_time."""
        if isinstance(value, str):
            # Handle formats like "07:16:46.128Z" or "07:16:46Z"
            # Strip timezone indicator and milliseconds
            time_str = value.replace('Z', '').split('.')[0]
            try:
                # Parse the time string (HH:MM:SS)
                time_parts = time_str.split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2]) if len(time_parts) > 2 else 0
                    from datetime import time
                    return time(hour=hour, minute=minute, second=second)
            except (ValueError, IndexError):
                # If parsing fails, let DRF handle the error
                pass
        return value

    def create(self, validated_data):
        """Create trip with capacity."""
        capacity_data = validated_data.pop("capacity")
        capacity = TripCapacity.objects.create(**capacity_data)
        trip = Trip.objects.create(capacity=capacity, **validated_data)
        return trip

    def update(self, instance, validated_data):
        """Update trip and capacity."""
        capacity_data = validated_data.pop("capacity", None)
        
        if capacity_data:
            # Update capacity
            for attr, value in capacity_data.items():
                setattr(instance.capacity, attr, value)
            instance.capacity.save()
        
        # Update trip
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class TripListSerializer(serializers.ModelSerializer):
    """Simplified serializer for trip listings."""

    capacity = TripCapacitySerializer(read_only=True)
    traveler_id = serializers.UUIDField(source="traveler.id", read_only=True)
    is_accepted = serializers.SerializerMethodField()
    completed_shipments_count = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "traveler_id",
            "first_name",
            "last_name",
            "mode",
            "status",
            "from_location",
            "to_location",
            "departure_date",
            "departure_time",
            "capacity",
            "category",
            "airline",
            "pickup_availability_start_date",
            "pickup_availability_end_date",
            "meeting_points",
            "is_accepted",
            "completed_shipments_count",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_accepted(self, obj) -> bool:
        """Check if the trip has any accepted requests."""
        if not obj.pk:
            return False
        return obj.requests.filter(status="accepted").exists()

    @extend_schema_field(OpenApiTypes.INT)
    def get_completed_shipments_count(self, obj) -> int:
        """Return the number of accepted requests for this trip."""
        if not obj.pk:
            return 0
        return obj.requests.filter(status="accepted").count()

    def to_representation(self, instance):
        """Return complete location and airline objects in response."""
        data = super().to_representation(instance)
        # Replace location UUIDs with full objects
        if instance.from_location:
            data['from_location'] = LocationSerializer(instance.from_location).data
        if instance.to_location:
            data['to_location'] = LocationSerializer(instance.to_location).data
        # Replace airline UUID with full object
        if instance.airline:
            data['airline'] = AirlineSerializer(instance.airline).data
        return data


class MyTripListSerializer(serializers.ModelSerializer):
    """Serializer for current user's trips with accepted request info."""

    capacity = TripCapacitySerializer(read_only=True)
    traveler_id = serializers.UUIDField(source="traveler.id", read_only=True)
    is_accepted = serializers.SerializerMethodField()
    completed_shipments_count = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "traveler_id",
            "first_name",
            "last_name",
            "mode",
            "status",
            "from_location",
            "to_location",
            "departure_date",
            "departure_time",
            "capacity",
            "category",
            "airline",
            "pickup_availability_start_date",
            "pickup_availability_end_date",
            "meeting_points",
            "is_accepted",
            "completed_shipments_count",
            "requests",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_accepted(self, obj) -> bool:
        """Check if the trip has any accepted requests."""
        if not obj.pk:
            return False
        return obj.requests.filter(status="accepted").exists()

    @extend_schema_field(OpenApiTypes.INT)
    def get_completed_shipments_count(self, obj) -> int:
        """Return the number of accepted requests for this trip."""
        if not obj.pk:
            return 0
        return obj.requests.filter(status="accepted").count()

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_requests(self, obj) -> list:
        """Get all accepted requests for this trip with shipment details."""
        from apps.requests.models import Request
        from apps.shipments.serializers import ShipmentListSerializer
        
        accepted_requests = obj.requests.filter(status="accepted").select_related(
            "sender", "receiver", "shipment"
        ).prefetch_related("shipment__items")
        
        requests_data = []
        for request in accepted_requests:
            request_data = {
                "id": str(request.id),
                "sender_id": str(request.sender.id),
                "receiver_id": str(request.receiver.id),
                "offered_price": str(request.offered_price),
                "status": request.status,
                "message": request.message,
                "created_at": request.created_at.isoformat() if request.created_at else None,
            }
            # Include shipment details if available
            if request.shipment:
                request_data["shipment"] = ShipmentListSerializer(request.shipment).data
            requests_data.append(request_data)
        
        return requests_data

    def to_representation(self, instance):
        """Return complete location and airline objects in response."""
        data = super().to_representation(instance)
        # Replace location UUIDs with full objects
        if instance.from_location:
            data['from_location'] = LocationSerializer(instance.from_location).data
        if instance.to_location:
            data['to_location'] = LocationSerializer(instance.to_location).data
        # Replace airline UUID with full object
        if instance.airline:
            data['airline'] = AirlineSerializer(instance.airline).data
        return data
