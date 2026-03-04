"""
Admin Panel serializers for Tramper.
"""

from rest_framework import serializers
from .models import ActivityLog
from apps.users.models import User


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for activity log entries."""

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "entity_type",
            "entity_id",
            "description",
            "metadata",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.full_name or obj.actor.username
        return "System"


class AdminLoginSerializer(serializers.Serializer):
    """Serializer for admin login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate

        email = data.get("email")
        password = data.get("password")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_staff:
            raise serializers.ValidationError("Access denied. Admin privileges required.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")

        data["user"] = user
        return data


class AdminVerifyOTPSerializer(serializers.Serializer):
    """Serializer for admin OTP verification."""

    email = serializers.EmailField()
    otp = serializers.CharField()
class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user info (used by /auth/me/)."""

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "username",
            "email",
            "profile_image_url",
            "is_staff",
            "is_superuser",
        ]


class DashboardMetricsSerializer(serializers.Serializer):
    """Serializer for dashboard metrics cards."""

    total_users = serializers.IntegerField()
    total_users_change = serializers.CharField()
    active_trips = serializers.IntegerField()
    active_trips_change = serializers.CharField()
    pending_shipments = serializers.IntegerField()
    pending_shipments_change = serializers.CharField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_revenue_change = serializers.CharField()


class TripsShipmentsOverTimeSerializer(serializers.Serializer):
    """Serializer for trips & shipments over time chart."""

    month = serializers.CharField()
    trips = serializers.IntegerField()
    shipments = serializers.IntegerField()


class RevenueByMonthSerializer(serializers.Serializer):
    """Serializer for revenue by month chart."""

    month = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class ShipmentStatusSerializer(serializers.Serializer):
    """Serializer for shipment status chart."""

    name = serializers.CharField()
    value = serializers.IntegerField()
    fill = serializers.CharField()


class RecentActivitySerializer(serializers.Serializer):
    """Serializer for recent activity feed (matches frontend format)."""

    id = serializers.UUIDField()
    type = serializers.CharField()
    message = serializers.CharField()
    time = serializers.CharField()


class TopRoutesSerializer(serializers.Serializer):
    """Serializer for top routes chart."""

    route = serializers.CharField()
    trips = serializers.IntegerField()
    shipments = serializers.IntegerField()


class WeeklyActivitySerializer(serializers.Serializer):
    """Serializer for weekly activity chart."""

    day = serializers.CharField()
    users = serializers.IntegerField()
    trips = serializers.IntegerField()
    shipments = serializers.IntegerField()


# ============================================================================
# LISTING PAGE SERIALIZERS
# ============================================================================


class AdminUserListSerializer(serializers.ModelSerializer):
    """Users list page — matches frontend User interface."""

    name = serializers.SerializerMethodField()
    phone = serializers.CharField(default="")
    role = serializers.SerializerMethodField()
    joinedDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "role", "joinedDate", "status"]

    def get_name(self, obj):
        return obj.full_name or obj.username

    def get_role(self, obj):
        # Users with trips are Travelers, with shipments are Senders
        if obj.total_trips and obj.total_trips > 0:
            return "Traveler"
        if obj.total_shipments and obj.total_shipments > 0:
            return "Sender"
        return "Traveler"

    def get_joinedDate(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d")
        return ""

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


class AdminTripListSerializer(serializers.Serializer):
    """Trips list page — matches frontend Trip interface."""

    id = serializers.UUIDField()
    travelerName = serializers.CharField()
    fromCity = serializers.CharField(source="from")
    toCity = serializers.CharField(source="to")
    date = serializers.CharField()
    capacity = serializers.CharField()
    status = serializers.CharField()


class AdminShipmentListSerializer(serializers.Serializer):
    """Shipments list page — matches frontend Shipment interface."""

    id = serializers.UUIDField()
    senderName = serializers.CharField()
    recipientCity = serializers.CharField()
    matchedTraveler = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    createdDate = serializers.CharField()
    parcelWeight = serializers.CharField()


class AdminPaymentSerializer(serializers.Serializer):
    """Payments list page — matches frontend Payment interface."""

    id = serializers.UUIDField()
    sender = serializers.CharField()
    traveler = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    date = serializers.CharField()
