"""
Admin Panel URL configuration for Tramper.
"""

from django.urls import path

from .views import (
    AdminLoginView,
    AdminLogoutView,
    AdminMeView,
    AdminTokenRefreshView,
    AdminVerifyOTPView,
    DashboardMetricsView,
    TripsShipmentsOverTimeView,
    RevenueByMonthView,
    ShipmentStatusView,
    RecentActivityView,
    TopRoutesView,
    WeeklyActivityView,
    AdminUsersListView,
    AdminUserToggleStatusView,
    AdminTripsListView,
    AdminShipmentsListView,
    AdminPaymentsListView,
)

urlpatterns = [
    # Auth
    path("auth/login/", AdminLoginView.as_view(), name="admin_login"),
    path("auth/verify-otp/", AdminVerifyOTPView.as_view(), name="admin_verify_otp"),
    path("auth/logout/", AdminLogoutView.as_view(), name="admin_logout"),
    path("auth/me/", AdminMeView.as_view(), name="admin_me"),
    path("auth/refresh/", AdminTokenRefreshView.as_view(), name="admin_token_refresh"),
    # Dashboard
    path("dashboard/metrics/", DashboardMetricsView.as_view(), name="dashboard_metrics"),
    path("dashboard/trips-shipments-over-time/", TripsShipmentsOverTimeView.as_view(), name="trips_shipments_over_time"),
    path("dashboard/revenue-by-month/", RevenueByMonthView.as_view(), name="revenue_by_month"),
    path("dashboard/shipment-status/", ShipmentStatusView.as_view(), name="shipment_status"),
    path("dashboard/recent-activity/", RecentActivityView.as_view(), name="recent_activity"),
    path("dashboard/top-routes/", TopRoutesView.as_view(), name="top_routes"),
    path("dashboard/weekly-activity/", WeeklyActivityView.as_view(), name="weekly_activity"),
    # Lists
    path("users/", AdminUsersListView.as_view(), name="admin_users_list"),
    path("users/<uuid:user_id>/toggle-status/", AdminUserToggleStatusView.as_view(), name="admin_user_toggle_status"),
    path("trips/", AdminTripsListView.as_view(), name="admin_trips_list"),
    path("shipments/", AdminShipmentsListView.as_view(), name="admin_shipments_list"),
    path("payments/", AdminPaymentsListView.as_view(), name="admin_payments_list"),
]
