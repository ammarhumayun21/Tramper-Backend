"""
Admin Panel views for Tramper.
Auth endpoints + Dashboard API views.
"""

from datetime import timedelta, date
from collections import Counter
import random

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth, TruncDate
from django.utils import timezone
from django.utils.timesince import timesince

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.api import success_response
from core.permissions import IsAdmin
from core.emails import send_admin_otp_email
from apps.users.models import User
from apps.trips.models import Trip, TripCapacity
from apps.shipments.models import Shipment, ShipmentItem
from apps.requests.models import Request
from apps.complaints.models import Complaint

from .models import ActivityLog
from .serializers import (
    AdminLoginSerializer,
    AdminVerifyOTPSerializer,
    AdminUserSerializer,
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminTripListSerializer,
    AdminShipmentListSerializer,
    AdminPaymentSerializer,
    DashboardMetricsSerializer,
    TripsShipmentsOverTimeSerializer,
    RevenueByMonthSerializer,
    ShipmentStatusSerializer,
    RecentActivitySerializer,
    TopRoutesSerializer,
    WeeklyActivitySerializer,
    ActivityLogSerializer,
    AdminProfileUpdateSerializer,
    AdminChangePasswordSerializer,
    AdminCreateSuperuserSerializer,
)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================


class AdminLoginView(APIView):
    """
    Admin login endpoint.
    Validates credentials, checks staff status, and sets HTTP-only cookies.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Admin Auth"],
        summary="Admin login",
        description="Authenticate as admin and receive HTTP-only cookie tokens.",
        request=AdminLoginSerializer,
        responses={
            200: OpenApiResponse(response=AdminUserSerializer, description="Login successful"),
            400: OpenApiResponse(description="Invalid credentials or not an admin"),
        },
    )
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate 6-digit OTP
        otp = f"{random.randint(100000, 999999)}"
        
        # Save to cache with 5-minute expiry
        cache_key = f"admin_otp_{user.email}"
        cache.set(cache_key, otp, timeout=300)
        
        # Send OTP email
        user_name = user.full_name or user.username
        send_admin_otp_email(user_email=user.email, otp=otp, user_name=user_name)

        return success_response({
            "message": "OTP sent successfully",
            "otp_required": True,
            "email": user.email,
        })


class AdminVerifyOTPView(APIView):
    """
    Admin OTP verification endpoint.
    Validates OTP from cache, checks user, and sets HTTP-only cookies.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Admin Auth"],
        summary="Admin OTP Verification",
        description="Verify OTP and receive HTTP-only cookie tokens.",
        request=AdminVerifyOTPSerializer,
        responses={
            200: OpenApiResponse(response=AdminUserSerializer, description="Login successful"),
            400: OpenApiResponse(description="Invalid OTP or expired"),
        },
    )
    def post(self, request):
        serializer = AdminVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        cache_key = f"admin_otp_{email}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or cached_otp != otp:
            return success_response(
                {"message": "Invalid or expired OTP"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Clear OTP
        cache.delete(cache_key)

        # Get user
        try:
            user = User.objects.get(email=email, is_staff=True, is_active=True)
        except User.DoesNotExist:
            return success_response(
                {"message": "User not found or disabled"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = success_response({
            "user": AdminUserSerializer(user).data,
        })

        # Set HTTP-only cookies
        is_secure = not settings.DEBUG
        samesite = "Lax" if settings.DEBUG else "None"

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=is_secure,
            samesite=samesite,
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=is_secure,
            samesite=samesite,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            path="/",
        )

        return response


class AdminLogoutView(APIView):
    """
    Admin logout endpoint.
    Clears authentication cookies.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Admin Auth"],
        summary="Admin logout",
        description="Clear authentication cookies.",
        responses={200: OpenApiResponse(description="Logout successful")},
    )
    def post(self, request):
        response = success_response({"message": "Logged out successfully"})
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")
        return response


class AdminMeView(APIView):
    """
    Get current admin user info.
    Used by frontend to check authentication state.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Auth"],
        summary="Get current admin user",
        description="Returns the current authenticated admin user information.",
        responses={
            200: OpenApiResponse(response=AdminUserSerializer, description="Current user info"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        return success_response(AdminUserSerializer(request.user).data)


class AdminProfileUpdateView(APIView):
    """
    Update current admin user profile (name, phone, profile_image).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=["Admin Auth"],
        summary="Update admin profile",
        description="Update current authenticated admin's full name, phone number, and profile image.",
        request=AdminProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(response=AdminUserSerializer, description="Profile updated"),
            400: OpenApiResponse(description="Invalid data"),
        },
    )
    def put(self, request):
        serializer = AdminProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.full_name = serializer.validated_data.get("full_name", user.full_name)
        user.phone = serializer.validated_data.get("phone", user.phone)
        
        profile_image = serializer.validated_data.get('profile_image', None)
        if profile_image:
            try:
                from core.storage import s3_storage
                profile_image_url = s3_storage.upload_image(profile_image, folder="avatars")
                user.profile_image_url = profile_image_url
                user.save(update_fields=["full_name", "phone", "profile_image_url", "updated_at"])
            except Exception as e:
                print(f"Failed to upload admin profile image: {str(e)}")
                user.save(update_fields=["full_name", "phone", "updated_at"])
        else:
            user.save(update_fields=["full_name", "phone", "updated_at"])
        
        return success_response({
            "message": "Profile updated successfully.",
            "user": AdminUserSerializer(user).data
        })


class AdminChangePasswordView(APIView):
    """
    Change current admin user password.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Auth"],
        summary="Change admin password",
        description="Change password for the currently authenticated admin.",
        request=AdminChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Invalid data or incorrect current password"),
        },
    )
    def post(self, request):
        serializer = AdminChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]
        
        if not user.check_password(current_password):
            return success_response(
                {"message": "Incorrect current password."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
            
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        
        return success_response({
            "message": "Password changed successfully."
        })


class AdminCreateSuperuserView(APIView):
    """
    Create a new superuser from the admin panel.
    Only accessible by existing superusers.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin Management"],
        summary="Create new superuser",
        description="Create a new admin user with is_staff and is_superuser set to True.",
        request=AdminCreateSuperuserSerializer,
        responses={
            201: OpenApiResponse(response=AdminUserSerializer, description="Superuser created"),
            400: OpenApiResponse(description="Invalid data or email already exists"),
            403: OpenApiResponse(description="Permission denied. Must be a superuser."),
        },
    )
    def post(self, request):
        if not request.user.is_superuser:
            return success_response(
                {"message": "Permission denied. Only superusers can create new superusers."},
                status_code=status.HTTP_403_FORBIDDEN,
            )
            
        serializer = AdminCreateSuperuserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data["email"]
        if User.objects.filter(email=email).exists():
            return success_response(
                {"message": "User with this email already exists."},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
            
        # Ensure a username is set, we can use email prefix or prompt for it
        # Model requires username, using email is safe fallback
        username = email.split('@')[0]
        # Make sure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = User.objects.create_superuser(
            email=email,
            password=serializer.validated_data["password"],
            username=username,
            full_name=serializer.validated_data.get("full_name", ""),
            phone=serializer.validated_data.get("phone", ""),
        )
        
        return success_response(
            {
                "message": "Superuser created successfully.",
                "user": AdminUserSerializer(user).data
            },
            status_code=status.HTTP_201_CREATED
        )


class AdminTokenRefreshView(APIView):
    """
    Refresh access token using the refresh token cookie.
    Sets a new access token cookie.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Admin Auth"],
        summary="Refresh admin token",
        description="Refresh the access token using the refresh token cookie.",
        responses={
            200: OpenApiResponse(description="Token refreshed"),
            401: OpenApiResponse(description="Invalid or expired refresh token"),
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return success_response(
                {"message": "No refresh token"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            response = success_response({"message": "Token refreshed"})

            is_secure = not settings.DEBUG
            samesite = "Lax" if settings.DEBUG else "None"

            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=is_secure,
                samesite=samesite,
                max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
                path="/",
            )

            return response
        except Exception:
            return success_response(
                {"message": "Invalid refresh token"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


# ============================================================================
# DASHBOARD VIEWS
# ============================================================================


def _calc_pct_change(current, previous):
    """Calculate percentage change between two values."""
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    change = ((current - previous) / previous) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.0f}%"


class DashboardMetricsView(APIView):
    """Dashboard metrics cards: Total Users, Active Trips, Pending Shipments, Total Revenue."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Dashboard metrics",
        description="Get dashboard stat card data.",
        responses={200: OpenApiResponse(response=DashboardMetricsSerializer)},
    )
    def get(self, request):
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

        # Total Users
        total_users = User.objects.count()
        users_prev = User.objects.filter(created_at__lt=current_month_start).count()
        users_new_this_month = User.objects.filter(created_at__gte=current_month_start).count()
        users_new_prev_month = User.objects.filter(
            created_at__gte=prev_month_start,
            created_at__lt=current_month_start,
        ).count()

        # Active Trips (valid + future departure)
        today = date.today()
        active_trips = Trip.objects.filter(status="valid", departure_date__gte=today).count()
        active_trips_prev = Trip.objects.filter(
            status="valid",
            departure_date__gte=prev_month_start.date(),
            departure_date__lt=current_month_start.date(),
        ).count()

        # Pending Shipments
        pending_shipments = Shipment.objects.filter(status="pending").count()
        pending_prev = Shipment.objects.filter(
            status="pending",
            created_at__gte=prev_month_start,
            created_at__lt=current_month_start,
        ).count()

        # Total Revenue (sum of rewards for delivered shipments)
        total_revenue = Shipment.objects.filter(
            status="delivered"
        ).aggregate(total=Sum("reward"))["total"] or 0

        revenue_this_month = Shipment.objects.filter(
            status="delivered",
            updated_at__gte=current_month_start,
        ).aggregate(total=Sum("reward"))["total"] or 0

        revenue_prev_month = Shipment.objects.filter(
            status="delivered",
            updated_at__gte=prev_month_start,
            updated_at__lt=current_month_start,
        ).aggregate(total=Sum("reward"))["total"] or 0

        data = {
            "total_users": total_users,
            "total_users_change": _calc_pct_change(users_new_this_month, users_new_prev_month),
            "active_trips": active_trips,
            "active_trips_change": _calc_pct_change(active_trips, active_trips_prev),
            "pending_shipments": pending_shipments,
            "pending_shipments_change": _calc_pct_change(pending_shipments, pending_prev),
            "total_revenue": total_revenue,
            "total_revenue_change": _calc_pct_change(revenue_this_month, revenue_prev_month),
        }

        return success_response(data)


class TripsShipmentsOverTimeView(APIView):
    """Trips & shipments created per month, last 6 months."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Trips & shipments over time",
        description="Get monthly trip and shipment counts for the last 6 months.",
        responses={200: OpenApiResponse(response=TripsShipmentsOverTimeSerializer(many=True))},
    )
    def get(self, request):
        now = timezone.now()
        six_months_ago = (now - timedelta(days=180)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        trip_counts = (
            Trip.objects.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        shipment_counts = (
            Shipment.objects.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        trip_map = {item["month"].strftime("%b"): item["count"] for item in trip_counts}
        shipment_map = {item["month"].strftime("%b"): item["count"] for item in shipment_counts}

        # Build list for last 6 months
        result = []
        for i in range(5, -1, -1):
            d = now - timedelta(days=30 * i)
            month_label = d.strftime("%b")
            result.append({
                "month": month_label,
                "trips": trip_map.get(month_label, 0),
                "shipments": shipment_map.get(month_label, 0),
            })

        return success_response(result)


class RevenueByMonthView(APIView):
    """Monthly revenue from delivered shipments, last 6 months."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Revenue by month",
        description="Get monthly revenue from delivered shipments for the last 6 months.",
        responses={200: OpenApiResponse(response=RevenueByMonthSerializer(many=True))},
    )
    def get(self, request):
        now = timezone.now()
        six_months_ago = (now - timedelta(days=180)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        revenue_data = (
            Shipment.objects.filter(
                status="delivered",
                updated_at__gte=six_months_ago,
            )
            .annotate(month=TruncMonth("updated_at"))
            .values("month")
            .annotate(revenue=Sum("reward"))
            .order_by("month")
        )

        revenue_map = {item["month"].strftime("%b"): item["revenue"] for item in revenue_data}

        result = []
        for i in range(5, -1, -1):
            d = now - timedelta(days=30 * i)
            month_label = d.strftime("%b")
            result.append({
                "month": month_label,
                "revenue": revenue_map.get(month_label, 0),
            })

        return success_response(result)


class ShipmentStatusView(APIView):
    """Shipment count by status with fill colors."""
    permission_classes = [IsAdmin]

    STATUS_COLORS = {
        "pending": "hsl(217, 91%, 60%)",
        "accepted": "hsl(152, 69%, 41%)",
        "in_transit": "hsl(38, 92%, 50%)",
        "delivered": "hsl(142, 71%, 45%)",
        "received": "hsl(200, 80%, 50%)",
        "cancelled": "hsl(0, 84%, 60%)",
    }

    STATUS_LABELS = {
        "pending": "Pending",
        "accepted": "Accepted",
        "in_transit": "In Transit",
        "delivered": "Delivered",
        "received": "Received",
        "cancelled": "Cancelled",
    }

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Shipment status",
        description="Get shipment counts grouped by status.",
        responses={200: OpenApiResponse(response=ShipmentStatusSerializer(many=True))},
    )
    def get(self, request):
        counts = (
            Shipment.objects.values("status")
            .annotate(value=Count("id"))
            .order_by("status")
        )

        result = []
        for item in counts:
            s = item["status"]
            result.append({
                "name": self.STATUS_LABELS.get(s, s.title()),
                "value": item["value"],
                "fill": self.STATUS_COLORS.get(s, "hsl(220, 13%, 60%)"),
            })

        return success_response(result)


class RecentActivityView(APIView):
    """Recent activity feed from ActivityLog."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Recent activity",
        description="Get the latest activity entries.",
        responses={200: OpenApiResponse(response=RecentActivitySerializer(many=True))},
    )
    def get(self, request):
        now = timezone.now()
        three_days_ago = now - timedelta(days=3)
        logs = ActivityLog.objects.select_related("actor").filter(
            created_at__gte=three_days_ago
        ).order_by("-created_at")
        
        result = []
        for log in logs:
            # Calculate relative time
            delta = now - log.created_at
            if delta.total_seconds() < 60:
                time_str = "just now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                time_str = f"{minutes} min ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                time_str = f"{hours} hr{'s' if hours > 1 else ''} ago"
            else:
                days = delta.days
                time_str = f"{days} day{'s' if days > 1 else ''} ago"

            result.append({
                "id": str(log.id),
                "type": log.entity_type,
                "message": log.description,
                "time": time_str,
            })

        return success_response(result)


class TopRoutesView(APIView):
    """Top routes by trip and shipment count."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Top routes",
        description="Get top routes by number of trips and shipments.",
        responses={200: OpenApiResponse(response=TopRoutesSerializer(many=True))},
    )
    def get(self, request):
        # Trips: group by from_location → to_location
        trip_routes = (
            Trip.objects.select_related("from_location", "to_location")
            .values(
                "from_location__iata_code",
                "to_location__iata_code",
            )
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Shipments: group by from_location → to_location
        shipment_routes = (
            Shipment.objects.select_related("from_location", "to_location")
            .values(
                "from_location__iata_code",
                "to_location__iata_code",
            )
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Merge into single list
        route_data = {}
        for tr in trip_routes:
            route_key = f"{tr['from_location__iata_code']} → {tr['to_location__iata_code']}"
            if route_key not in route_data:
                route_data[route_key] = {"route": route_key, "trips": 0, "shipments": 0}
            route_data[route_key]["trips"] = tr["count"]

        for sr in shipment_routes:
            route_key = f"{sr['from_location__iata_code']} → {sr['to_location__iata_code']}"
            if route_key not in route_data:
                route_data[route_key] = {"route": route_key, "trips": 0, "shipments": 0}
            route_data[route_key]["shipments"] = sr["count"]

        # Sort by total and take top 5
        sorted_routes = sorted(
            route_data.values(),
            key=lambda x: x["trips"] + x["shipments"],
            reverse=True,
        )[:5]

        return success_response(sorted_routes)


class WeeklyActivityView(APIView):
    """Weekly activity: users registered, trips created, shipments created per day (last 7 days)."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Dashboard"],
        summary="Weekly activity",
        description="Get daily activity counts for users, trips, and shipments over the last 7 days.",
        responses={200: OpenApiResponse(response=WeeklyActivitySerializer(many=True))},
    )
    def get(self, request):
        now = timezone.now()
        seven_days_ago = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

        user_counts = (
            User.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )

        trip_counts = (
            Trip.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )

        shipment_counts = (
            Shipment.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )

        user_map = {item["day"]: item["count"] for item in user_counts}
        trip_map = {item["day"]: item["count"] for item in trip_counts}
        shipment_map = {item["day"]: item["count"] for item in shipment_counts}

        result = []
        for i in range(6, -1, -1):
            d = (now - timedelta(days=i)).date()
            result.append({
                "day": d.strftime("%a"),
                "users": user_map.get(d, 0),
                "trips": trip_map.get(d, 0),
                "shipments": shipment_map.get(d, 0),
            })

        return success_response(result)


# ============================================================================
# LISTING VIEWS (Users, Trips, Shipments, Payments)
# ============================================================================


class AdminUsersListView(APIView):
    """List all users for admin panel with search, filter, and pagination."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Management"],
        summary="List all users",
        description="Returns paginated user list with search and role filter.",
        responses={200: OpenApiResponse(response=AdminUserListSerializer(many=True))},
    )
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        role = request.query_params.get("role", "all")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = User.objects.all().annotate(
            trip_count=Count("trips"),
            shipment_count=Count("sent_shipments"),
        ).order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
            )

        if role == "Traveler":
            qs = qs.filter(trip_count__gt=0)
        elif role == "Sender":
            qs = qs.filter(shipment_count__gt=0)
        elif role == "User":
            qs = qs.filter(trip_count=0, shipment_count=0, is_superuser=False, is_staff=False)
        elif role == "Admin":
            qs = qs.filter(Q(is_superuser=True) | Q(is_staff=True))

        status_filter = request.query_params.get("status", "all")
        if status_filter == "Active":
            qs = qs.filter(is_active=True)
        elif status_filter == "Inactive":
            qs = qs.filter(is_active=False)

        total = qs.count()
        start = (page - 1) * page_size
        users = qs[start : start + page_size]

        serializer = AdminUserListSerializer(users, many=True)
        return success_response({
            "results": serializer.data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class AdminUserToggleStatusView(APIView):
    """Toggle user active/inactive status."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Management"],
        summary="Toggle user status",
        description="Activate or deactivate a user account.",
    )
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return success_response(
                {"message": "User not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        return success_response({
            "id": str(user.id),
            "status": "Active" if user.is_active else "Inactive",
        })


class AdminUserDetailView(APIView):
    """Get full user detail for admin panel."""
    permission_classes = [IsAdmin]

    def get(self, request, user_id):
        try:
            user = User.objects.prefetch_related(
                "verification_requests"
            ).select_related("settings").get(id=user_id)
        except User.DoesNotExist:
            return success_response(
                {"message": "User not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = AdminUserDetailSerializer(user)
        return success_response(serializer.data)


class AdminUserTripsView(APIView):
    """Get all trips for a specific user."""
    permission_classes = [IsAdmin]

    STATUS_MAP = {
        "valid": "Approved",
        "invalid": "Cancelled",
    }

    def get(self, request, user_id):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Trip.objects.filter(traveler_id=user_id).select_related(
            "traveler", "from_location", "to_location", "capacity", "airline", "category"
        ).order_by("-departure_date")

        total = qs.count()
        start = (page - 1) * page_size
        trips = qs[start : start + page_size]

        result = []
        for trip in trips:
            cap = trip.capacity
            if trip.status == "invalid":
                status_str = "Cancelled"
            elif trip.status == "completed":
                status_str = "Completed"
            elif not trip.is_approved:
                status_str = "Pending Approval"
            else:
                status_str = "Approved"

            result.append({
                "id": str(trip.id),
                "from": trip.from_location.iata_code or trip.from_location.city,
                "to": trip.to_location.iata_code or trip.to_location.city,
                "fromCity": trip.from_location.city,
                "toCity": trip.to_location.city,
                "date": trip.departure_date.strftime("%Y-%m-%d"),
                "departureTime": trip.departure_time.strftime("%H:%M") if trip.departure_time else None,
                "capacity": f"{cap.total_weight} {cap.unit}" if cap else "N/A",
                "status": status_str,
                "mode": trip.mode,
                "category": trip.category.name if trip.category else "",
                "airline": trip.airline.name if trip.airline else None,
            })

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class AdminUserShipmentsView(APIView):
    """Get all shipments for a specific user (as sender)."""
    permission_classes = [IsAdmin]

    STATUS_LABELS = {
        "pending": "Pending",
        "accepted": "Matched",
        "in_transit": "In Transit",
        "delivered": "Delivered",
        "received": "Delivered",
        "cancelled": "Disputed",
    }

    def get(self, request, user_id):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Shipment.objects.filter(sender_id=user_id).select_related(
            "sender", "traveler", "from_location", "to_location"
        ).prefetch_related("items", "items__category").order_by("-created_at")

        total = qs.count()
        start = (page - 1) * page_size
        shipments = qs[start : start + page_size]

        result = []
        for s in shipments:
            total_weight = sum(
                float(item.single_item_weight * item.quantity)
                for item in s.items.all()
            )
            weight_str = f"{total_weight:.1f} kg" if total_weight else "N/A"
            status_str = self.STATUS_LABELS.get(s.status, s.status.title())

            result.append({
                "id": str(s.id),
                "name": s.name,
                "fromCity": s.from_location.city if s.from_location else "Unknown",
                "recipientCity": s.to_location.city if s.to_location else "Unknown",
                "matchedTraveler": (s.traveler.full_name or s.traveler.username) if s.traveler else None,
                "status": status_str,
                "createdDate": s.created_at.strftime("%Y-%m-%d"),
                "parcelWeight": weight_str,
                "reward": str(s.reward) if s.reward else "0",
                "itemCount": s.items.count(),
            })

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class AdminTripsListView(APIView):
    """List all trips for admin panel with search, filter, and pagination."""
    permission_classes = [IsAdmin]

    STATUS_MAP = {
        "valid": "Approved",
        "invalid": "Cancelled",
    }

    @extend_schema(
        tags=["Admin Management"],
        summary="List all trips",
        description="Returns paginated trip list with search and status filter.",
        responses={200: OpenApiResponse(response=AdminTripListSerializer(many=True))},
    )
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "all")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Trip.objects.select_related(
            "traveler", "from_location", "to_location", "capacity", "airline"
        ).select_related("category").order_by("-departure_date")

        if search:
            qs = qs.filter(
                Q(traveler__full_name__icontains=search)
                | Q(from_location__city__icontains=search)
                | Q(to_location__city__icontains=search)
                | Q(from_location__iata_code__icontains=search)
                | Q(to_location__iata_code__icontains=search)
            )

        # Map frontend status names to backend status values
        if status_filter == "Approved":
            qs = qs.filter(is_approved=True, status="valid")
        elif status_filter == "Pending Approval":
            qs = qs.filter(is_approved=False, status="valid")
        elif status_filter == "Cancelled":
            qs = qs.filter(status="invalid")
        elif status_filter == "Completed":
            qs = qs.filter(status="completed")

        total = qs.count()
        start = (page - 1) * page_size
        trips = qs[start : start + page_size]

        result = []
        for trip in trips:
            cap = trip.capacity
            # Map status
            if trip.status == "invalid":
                status_str = "Cancelled"
            elif trip.status == "completed":
                status_str = "Completed"
            elif not trip.is_approved:
                status_str = "Pending Approval"
            else:
                status_str = "Approved"

            result.append({
                "id": str(trip.id),
                "travelerName": trip.traveler.full_name or trip.traveler.username,
                "travelerAvatar": trip.traveler.profile_image_url if trip.traveler else None,
                "from": trip.from_location.iata_code or trip.from_location.city,
                "to": trip.to_location.iata_code or trip.to_location.city,
                "fromCity": trip.from_location.city,
                "fromCountry": trip.from_location.country if hasattr(trip.from_location, 'country') else "",
                "toCity": trip.to_location.city,
                "toCountry": trip.to_location.country if hasattr(trip.to_location, 'country') else "",
                "date": trip.departure_date.strftime("%Y-%m-%d"),
                "departureTime": trip.departure_time.strftime("%H:%M") if trip.departure_time else None,
                "capacity": f"{cap.total_weight} {cap.unit}" if cap else "N/A",
                "usedWeight": str(cap.used_weight) if cap else "0",
                "availableWeight": str(cap.available_weight) if cap else "0",
                "ticketImage": trip.ticket_image or None,
                "status": status_str,
                "mode": trip.mode,
                "category": trip.category.name if trip.category else "",
                "bookingReference": trip.booking_reference or "",
                "transportDetails": trip.transport_details or "",
                "notes": trip.notes or "",
                "airline": trip.airline.name if trip.airline else None,
                "meetingPoints": trip.meeting_points or [],
                "pickupStartDate": trip.pickup_availability_start_date.strftime("%Y-%m-%d") if trip.pickup_availability_start_date else None,
                "pickupEndDate": trip.pickup_availability_end_date.strftime("%Y-%m-%d") if trip.pickup_availability_end_date else None,
            })

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class AdminTripUpdateStatusView(APIView):
    """Update trip status (approve/cancel)."""
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Management"],
        summary="Update trip status (admin approve/cancel)",
    )
    def patch(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id)
        except Trip.DoesNotExist:
            return success_response(
                {"message": "Trip not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        status_str = request.data.get("status")
        if status_str == "Approved":
            trip.is_approved = True
            trip.status = "valid"
            trip.save(update_fields=["is_approved", "status"])
        elif status_str == "Cancelled":
            trip.is_approved = False
            trip.status = "invalid"
            trip.save(update_fields=["is_approved", "status"])

        return success_response({"id": str(trip.id), "status": status_str})


class AdminShipmentsListView(APIView):
    """List all shipments for admin panel with search, filter, and pagination."""
    permission_classes = [IsAdmin]

    STATUS_LABELS = {
        "pending": "Pending",
        "accepted": "Matched",
        "in_transit": "In Transit",
        "delivered": "Delivered",
        "received": "Delivered",
        "cancelled": "Disputed",
    }

    @extend_schema(
        tags=["Admin Management"],
        summary="List all shipments",
        description="Returns paginated shipment list with search and status filter.",
        responses={200: OpenApiResponse(response=AdminShipmentListSerializer(many=True))},
    )
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "all")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Shipment.objects.select_related(
            "sender", "traveler", "from_location", "to_location"
        ).prefetch_related("items", "items__category", "items__dimensions").order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(sender__full_name__icontains=search)
                | Q(to_location__city__icontains=search)
                | Q(traveler__full_name__icontains=search)
                | Q(name__icontains=search)
            )

        # Map frontend status to backend
        status_reverse = {
            "Pending": "pending",
            "Matched": "accepted",
            "In Transit": "in_transit",
            "Delivered": ["delivered", "received"],
            "Disputed": "cancelled",
        }
        if status_filter != "all" and status_filter in status_reverse:
            val = status_reverse[status_filter]
            if isinstance(val, list):
                qs = qs.filter(status__in=val)
            else:
                qs = qs.filter(status=val)

        total = qs.count()
        start = (page - 1) * page_size
        shipments = qs[start : start + page_size]

        result = []
        for s in shipments:
            # Calculate total weight from items
            total_weight = sum(
                float(item.single_item_weight * item.quantity)
                for item in s.items.all()
            )
            weight_str = f"{total_weight:.1f} kg" if total_weight else "N/A"

            # Map status
            status_str = self.STATUS_LABELS.get(s.status, s.status.title())

            result.append({
                "id": str(s.id),
                "senderName": s.sender.full_name or s.sender.username,
                "senderAvatar": s.sender.profile_image_url if s.sender else None,
                "name": s.name,
                "notes": s.notes or "",
                "fromCity": s.from_location.city if s.from_location else "Unknown",
                "fromCountry": s.from_location.country if s.from_location else "",
                "recipientCity": s.to_location.city if s.to_location else "Unknown",
                "toCountry": s.to_location.country if s.to_location else "",
                "matchedTraveler": (
                    s.traveler.full_name or s.traveler.username
                ) if s.traveler else None,
                "travelerAvatar": s.traveler.profile_image_url if s.traveler else None,
                "status": status_str,
                "createdDate": s.created_at.strftime("%Y-%m-%d"),
                "travelDate": s.travel_date.strftime("%Y-%m-%d") if s.travel_date else None,
                "parcelWeight": weight_str,
                "reward": str(s.reward) if s.reward else "0",
                "items": [
                    {
                        "id": str(item.id),
                        "name": item.name,
                        "link": item.link or "",
                        "category": item.category.name if item.category else "",
                        "quantity": item.quantity,
                        "singleItemPrice": str(item.single_item_price),
                        "singleItemWeight": str(item.single_item_weight),
                        "weightUnit": item.weight_unit,
                        "totalPrice": str(item.total_price),
                        "totalWeight": str(item.total_weight),
                        "imageUrls": item.image_urls or [],
                        "dimensions": {
                            "height": str(item.dimensions.height) if item.dimensions and item.dimensions.height else None,
                            "width": str(item.dimensions.width) if item.dimensions and item.dimensions.width else None,
                            "length": str(item.dimensions.length) if item.dimensions and item.dimensions.length else None,
                            "unit": item.dimensions.unit if item.dimensions else None,
                        } if item.dimensions else None,
                    }
                    for item in s.items.all()
                ],
            })

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })



class AdminPaymentsListView(APIView):
    """
    List all payments for admin panel.
    Payments are derived from shipments that have a reward (delivered/accepted).
    """
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin Management"],
        summary="List all payments",
        description="Returns paginated payment list.",
        responses={200: OpenApiResponse(response=AdminPaymentSerializer(many=True))},
    )
    def get(self, request):
        search = request.query_params.get("search", "").strip()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Shipment.objects.select_related(
            "sender", "traveler"
        ).filter(
            reward__gt=0,
        ).order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(sender__full_name__icontains=search)
                | Q(traveler__full_name__icontains=search)
                | Q(status__icontains=search)
            )

        total = qs.count()
        start = (page - 1) * page_size
        shipments = qs[start : start + page_size]

        status_map = {
            "pending": "Pending",
            "accepted": "Pending",
            "in_transit": "Pending",
            "delivered": "Completed",
            "received": "Completed",
            "cancelled": "Refunded",
        }

        result = []
        for s in shipments:
            result.append({
                "id": str(s.id),
                "sender": s.sender.full_name or s.sender.username,
                "traveler": (
                    s.traveler.full_name or s.traveler.username
                ) if s.traveler else "Unassigned",
                "amount": float(s.reward),
                "status": status_map.get(s.status, "Pending"),
                "date": s.created_at.strftime("%Y-%m-%d"),
            })

        # Calculate summary stats
        all_payments = Shipment.objects.filter(reward__gt=0)
        total_revenue = float(
            all_payments.filter(status__in=["delivered", "received"]).aggregate(
                total=Sum("reward")
            )["total"] or 0
        )
        pending_payouts = float(
            all_payments.filter(
                status__in=["pending", "accepted", "in_transit"]
            ).aggregate(total=Sum("reward"))["total"] or 0
        )
        completed_count = all_payments.filter(
            status__in=["delivered", "received"]
        ).count()

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "summary": {
                "total_revenue": total_revenue,
                "pending_payouts": pending_payouts,
                "completed_count": completed_count,
            },
        })


# ============================================================================
# COMPLAINTS VIEWS
# ============================================================================


class AdminComplaintsListView(APIView):
    """List all complaints for admin panel with search, filter, and pagination."""
    permission_classes = [IsAdmin]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "all")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        qs = Complaint.objects.select_related("user").order_by("-created_at")

        if search:
            qs = qs.filter(
                Q(subject__icontains=search)
                | Q(description__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        if status_filter and status_filter != "all":
            qs = qs.filter(status=status_filter)

        total = qs.count()
        start = (page - 1) * page_size
        complaints = qs[start : start + page_size]

        result = []
        for c in complaints:
            result.append({
                "id": str(c.id),
                "userName": c.user.full_name or c.user.username,
                "userEmail": c.user.email,
                "userAvatar": c.user.profile_image_url if hasattr(c.user, "profile_image_url") else None,
                "subject": c.subject,
                "description": c.description,
                "status": c.status,
                "adminResponse": c.admin_response,
                "createdAt": c.created_at.strftime("%Y-%m-%d %H:%M"),
                "updatedAt": c.updated_at.strftime("%Y-%m-%d %H:%M"),
            })

        return success_response({
            "results": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        })


class AdminComplaintUpdateStatusView(APIView):
    """Update complaint status."""
    permission_classes = [IsAdmin]

    def patch(self, request, complaint_id):
        try:
            complaint = Complaint.objects.get(id=complaint_id)
        except Complaint.DoesNotExist:
            return success_response(
                {"message": "Complaint not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        new_status = request.data.get("status")
        valid_statuses = [c[0] for c in Complaint.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return success_response(
                {"message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        complaint.status = new_status
        admin_response = request.data.get("admin_response")
        if admin_response is not None:
            complaint.admin_response = admin_response
        complaint.save()

        return success_response({"message": "Complaint updated successfully"})


class AdminComplaintSendEmailView(APIView):
    """Send an email to the complaint user from admin."""
    permission_classes = [IsAdmin]

    def post(self, request, complaint_id):
        try:
            complaint = Complaint.objects.select_related("user").get(id=complaint_id)
        except Complaint.DoesNotExist:
            return success_response(
                {"message": "Complaint not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        subject = request.data.get("subject", "")
        message = request.data.get("message", "")

        if not subject or not message:
            return success_response(
                {"message": "Subject and message are required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings as django_settings

        user_name = complaint.user.full_name or complaint.user.username
        html_content = (
            f"<p>Hello {user_name},</p>"
            f"<p>{message}</p>"
            f"<br/><p>Regarding your complaint: <strong>{complaint.subject}</strong></p>"
            f"<br/><p>Best regards,<br/>Tramper Support Team</p>"
        )
        text_content = (
            f"Hello {user_name},\n\n"
            f"{message}\n\n"
            f"Regarding your complaint: {complaint.subject}\n\n"
            f"Best regards,\nTramper Support Team"
        )

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[complaint.user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)
            sent = True
        except Exception:
            sent = False

        if sent:
            return success_response({"message": "Email sent successfully"})
        return success_response(
            {"message": "Failed to send email"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
