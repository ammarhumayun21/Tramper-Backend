"""
Verification center URLs for Tramper.
"""

from django.urls import path
from .views import (
    VerificationSubmitView,
    AdminVerificationListView,
    AdminVerificationDetailView,
)

urlpatterns = [
    # User endpoints
    path("submit/", VerificationSubmitView.as_view(), name="verification_submit"),
    # Admin endpoints
    path("admin/", AdminVerificationListView.as_view(), name="verification_admin_list"),
    path("admin/<uuid:pk>/", AdminVerificationDetailView.as_view(), name="verification_admin_detail"),
]
