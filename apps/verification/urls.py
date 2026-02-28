"""
Verification center URLs for Tramper.
"""

from django.urls import path
from .views import (
    VerificationSubmitView,
    PhoneVerifyView,
    AdminVerificationListView,
    AdminVerificationDetailView,
)

urlpatterns = [
    # User endpoints
    path("submit/", VerificationSubmitView.as_view(), name="verification_submit"),
    path("verify/phone/", PhoneVerifyView.as_view(), name="phone_verify"),
    # Admin endpoints
    path("admin/", AdminVerificationListView.as_view(), name="verification_admin_list"),
    path("admin/<uuid:pk>/", AdminVerificationDetailView.as_view(), name="verification_admin_detail"),
]
