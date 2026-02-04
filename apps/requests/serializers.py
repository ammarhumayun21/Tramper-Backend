"""
Request serializers for Tramper.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Request, CounterOffer
from apps.shipments.serializers import ShipmentListSerializer
from apps.trips.serializers import TripListSerializer


class CounterOfferSerializer(serializers.ModelSerializer):
    """Serializer for counter offers."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    receiver_id = serializers.UUIDField(source="receiver.id", read_only=True)

    class Meta:
        model = CounterOffer
        fields = [
            "id",
            "sender_id",
            "receiver_id",
            "request",
            "price",
            "message",
            "created_at",
        ]
        read_only_fields = ["id", "sender_id", "receiver_id", "request", "created_at"]


class CounterOfferCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating counter offers."""

    class Meta:
        model = CounterOffer
        fields = [
            "price",
            "message",
        ]

    def validate_price(self, value):
        """Ensure price is positive."""
        if value <= 0:
            raise serializers.ValidationError(_("Price must be greater than 0."))
        return value


class RequestSerializer(serializers.ModelSerializer):
    """Serializer for request data."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    receiver_id = serializers.UUIDField(source="receiver.id", read_only=True)
    shipment_id = serializers.UUIDField(source="shipment.id", read_only=True, allow_null=True)
    trip_id = serializers.UUIDField(source="trip.id", read_only=True, allow_null=True)
    counter_offers = CounterOfferSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # Include related objects for convenience
    shipment = ShipmentListSerializer(read_only=True)
    trip = TripListSerializer(read_only=True)

    class Meta:
        model = Request
        fields = [
            "id",
            "sender_id",
            "receiver_id",
            "shipment_id",
            "shipment",
            "trip_id",
            "trip",
            "offered_price",
            "current_price",
            "status",
            "message",
            "counter_offers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "sender_id",
            "receiver_id",
            "shipment_id",
            "trip_id",
            "current_price",
            "created_at",
            "updated_at",
        ]


class RequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing requests."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    receiver_id = serializers.UUIDField(source="receiver.id", read_only=True)
    shipment_id = serializers.UUIDField(source="shipment.id", read_only=True, allow_null=True)
    trip_id = serializers.UUIDField(source="trip.id", read_only=True, allow_null=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    counter_offers_count = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            "id",
            "sender_id",
            "receiver_id",
            "shipment_id",
            "trip_id",
            "offered_price",
            "current_price",
            "status",
            "counter_offers_count",
            "created_at",
            "updated_at",
        ]

    def get_counter_offers_count(self, obj):
        """Get count of counter offers."""
        return obj.counter_offers.count()


class RequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating requests."""

    receiver_id = serializers.UUIDField(write_only=True)
    shipment_id = serializers.UUIDField(required=False, allow_null=True)
    trip_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Request
        fields = [
            "receiver_id",
            "shipment_id",
            "trip_id",
            "offered_price",
            "message",
        ]

    def validate(self, attrs):
        """Validate request data."""
        shipment_id = attrs.get("shipment_id")
        trip_id = attrs.get("trip_id")
        receiver_id = attrs.get("receiver_id")
        sender = self.context["request"].user

        # Must have at least shipment or trip
        if not shipment_id and not trip_id:
            raise serializers.ValidationError(
                _("Either shipment_id or trip_id is required.")
            )

        # Cannot send request to yourself
        if str(receiver_id) == str(sender.id):
            raise serializers.ValidationError(
                {"receiver_id": _("Cannot send request to yourself.")}
            )

        # Validate shipment exists
        if shipment_id:
            from apps.shipments.models import Shipment
            try:
                shipment = Shipment.objects.get(pk=shipment_id)
                attrs["shipment"] = shipment
            except Shipment.DoesNotExist:
                raise serializers.ValidationError(
                    {"shipment_id": _("Shipment not found.")}
                )

        # Validate trip exists
        if trip_id:
            from apps.trips.models import Trip
            try:
                trip = Trip.objects.get(pk=trip_id)
                attrs["trip"] = trip
            except Trip.DoesNotExist:
                raise serializers.ValidationError(
                    {"trip_id": _("Trip not found.")}
                )

        # Validate receiver exists
        from apps.users.models import User
        try:
            receiver = User.objects.get(pk=receiver_id)
            attrs["receiver"] = receiver
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"receiver_id": _("User not found.")}
            )

        # Remove the _id fields as we now have the objects
        attrs.pop("receiver_id", None)
        attrs.pop("shipment_id", None)
        attrs.pop("trip_id", None)

        return attrs

    def create(self, validated_data):
        """Create request."""
        return Request.objects.create(**validated_data)


class RequestUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating request status."""

    class Meta:
        model = Request
        fields = [
            "status",
        ]

    def validate_status(self, value):
        """Validate status transitions."""
        instance = self.instance
        user = self.context["request"].user
        
        # Only receiver can accept/reject/counter
        if value in ["accepted", "rejected", "countered"]:
            if instance.receiver != user:
                raise serializers.ValidationError(
                    _("Only the receiver can accept, reject, or counter a request.")
                )
        
        # Only sender can cancel
        if value == "cancelled":
            if instance.sender != user:
                raise serializers.ValidationError(
                    _("Only the sender can cancel a request.")
                )
        
        # Cannot change from final states
        if instance.status in ["accepted", "rejected", "cancelled", "expired"]:
            raise serializers.ValidationError(
                _("Cannot change status of a finalized request.")
            )
        
        return value
