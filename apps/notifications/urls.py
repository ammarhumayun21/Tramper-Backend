"""
URL configuration for notifications app.
"""

from django.urls import path
from .views import (
    MyNotificationsView,
    UnreadCountView,
    MarkNotificationsReadView,
    NotificationDetailView,
    RegisterDeviceTokenView,
    DeleteDeviceTokenView,
)

app_name = "notifications"

urlpatterns = [
    # My notifications
    path("", MyNotificationsView.as_view(), name="my-notifications"),
    
    # Unread count
    path("unread-count/", UnreadCountView.as_view(), name="unread-count"),
    
    # Mark as read
    path("mark-read/", MarkNotificationsReadView.as_view(), name="mark-read"),
    
    # Notification detail
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="notification-detail"),

    # FCM device token management
    path("register-token/", RegisterDeviceTokenView.as_view(), name="register-token"),
    path("delete-token/", DeleteDeviceTokenView.as_view(), name="delete-token"),
]
