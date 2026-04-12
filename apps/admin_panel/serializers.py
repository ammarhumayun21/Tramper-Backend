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
            "phone",
            "profile_image_url",
            "is_staff",
            "is_superuser",
            "created_at",
            "last_login",
        ]


class AdminProfileUpdateSerializer(serializers.Serializer):
    """Serializer for updating admin profile."""

    full_name = serializers.CharField(required=True, max_length=255)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    profile_image = serializers.ImageField(required=False, write_only=True)


class AdminChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing admin password."""

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class AdminCreateSuperuserSerializer(serializers.Serializer):
    """Serializer for creating a new superuser from preferences."""

    full_name = serializers.CharField(required=True, max_length=255)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(required=True, min_length=8)
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
    roles = serializers.SerializerMethodField()
    joinedDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    avatar = serializers.CharField(source='profile_image_url', default='')

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "roles", "joinedDate", "status", "avatar"]

    def get_name(self, obj):
        return obj.full_name or obj.username

    def get_roles(self, obj):
        roles = []
        if obj.is_superuser or obj.is_staff:
            roles.append("Admin")
        if obj.trips.count() > 0:
            roles.append("Traveler")
        if obj.sent_shipments.count() > 0:
            roles.append("Sender")
        if not roles:
            roles.append("User")
        return roles

    def get_joinedDate(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d")
        return ""

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Full user detail for admin — includes settings and verification."""

    name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    joinedDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    avatar = serializers.CharField(source='profile_image_url', default='')
    total_trips = serializers.SerializerMethodField()
    total_shipments = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()
    verification = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "phone", "username", "roles", "joinedDate",
            "status", "avatar", "address", "city", "country", "bio", "rating",
            "total_trips", "total_deals", "total_shipments",
            "is_email_verified", "is_phone_verified", "is_user_verified",
            "is_staff", "is_superuser", "last_login", "settings", "verification",
        ]

    def get_total_trips(self, obj):
        return obj.trips.count()

    def get_total_shipments(self, obj):
        return obj.sent_shipments.count()

    def get_name(self, obj):
        return obj.full_name or obj.username

    def get_roles(self, obj):
        roles = []
        if obj.is_superuser or obj.is_staff:
            roles.append("Admin")
        if obj.trips.count() > 0:
            roles.append("Traveler")
        if obj.sent_shipments.count() > 0:
            roles.append("Sender")
        if not roles:
            roles.append("User")
        return roles

    def get_joinedDate(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d")
        return ""

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"

    def get_settings(self, obj):
        try:
            s = obj.settings
            return {
                "matchmaking_notifications_enabled": s.matchmaking_notifications_enabled,
                "chat_notifications_enabled": s.chat_notifications_enabled,
                "selected_language_code": s.selected_language_code,
                "ziina_username": s.ziina_username,
            }
        except Exception:
            return None

    def get_verification(self, obj):
        vr = obj.verification_requests.order_by("-created_at").first()
        if not vr:
            return None
        return {
            "id": str(vr.id),
            "status": vr.status,
            "id_card_number": vr.id_card_number or "",
            "phone_number": vr.phone_number or "",
            "id_card_front_url": vr.id_card_front_url or "",
            "id_card_back_url": vr.id_card_back_url or "",
            "selfie_with_id_url": vr.selfie_with_id_url or "",
            "admin_notes": vr.admin_notes or "",
            "created_at": vr.created_at.isoformat() if vr.created_at else "",
        }


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
    sender_avatar = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    traveler = serializers.CharField()
    traveler_avatar = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_charged = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    receiver_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    tramper_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    ziina_payment_intent_id = serializers.CharField(allow_blank=True, allow_null=True)
    ziina_redirect_url = serializers.CharField(allow_blank=True, allow_null=True)
    status = serializers.CharField()
    date = serializers.CharField()
    shipment_id = serializers.UUIDField(allow_null=True)
    shipment_name = serializers.CharField(allow_null=True, allow_blank=True)


class AdminWalletTransactionSerializer(serializers.Serializer):
    """Wallet transactions list page for admin."""

    id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    user_name = serializers.CharField()
    user_avatar = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField()
    date = serializers.CharField()
    reference_payment_id = serializers.UUIDField(allow_null=True)
    shipment_name = serializers.CharField(allow_null=True, allow_blank=True)
