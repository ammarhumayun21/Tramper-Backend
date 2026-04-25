"""
Notification views for Tramper.
"""

import logging

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Notification, DeviceToken
from .serializers import (
    NotificationSerializer,
    NotificationMarkReadSerializer,
    DeviceTokenRegisterSerializer,
    DeviceTokenDeleteSerializer,
    DeviceTokenSerializer,
)
from core.api import success_response

logger = logging.getLogger(__name__)


class MyNotificationsView(ListAPIView):
    """
    List current user's notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get notifications for current user."""
        # Handle swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by category if provided
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by is_read if provided
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == "true")
        
        return queryset.order_by("-timestamp")

    @extend_schema(
        tags=["Notifications"],
        summary="Get my notifications",
        description="Get all notifications for the current user.",
        parameters=[
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by category: request, counter_offer, shipment, trip, system"),
            OpenApiParameter("is_read", OpenApiTypes.BOOL, description="Filter by read status"),
        ],
        responses={
            200: OpenApiResponse(response=NotificationSerializer(many=True), description="List of notifications"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UnreadCountView(APIView):
    """
    Get unread notification count.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Get unread count",
        description="Get the count of unread notifications for the current user.",
        responses={
            200: OpenApiResponse(description="Unread count"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return success_response({"unread_count": count})


class MarkNotificationsReadView(APIView):
    """
    Mark notifications as read.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Mark notifications as read",
        description="Mark specific notifications or all notifications as read.",
        request=NotificationMarkReadSerializer,
        responses={
            200: OpenApiResponse(description="Notifications marked as read"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data.get("notification_ids", [])
        
        queryset = Notification.objects.filter(user=request.user, is_read=False)
        
        if notification_ids:
            queryset = queryset.filter(id__in=notification_ids)
        
        updated_count = queryset.update(is_read=True)
        
        return success_response({
            "message": f"{updated_count} notification(s) marked as read",
            "updated_count": updated_count,
        })


class NotificationDetailView(APIView):
    """
    Get or delete a specific notification.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        """Get notification by ID for current user."""
        try:
            return Notification.objects.get(pk=pk, user=self.request.user)
        except Notification.DoesNotExist:
            return None

    @extend_schema(
        tags=["Notifications"],
        summary="Get notification detail",
        description="Get a specific notification and mark it as read.",
        responses={
            200: OpenApiResponse(response=NotificationSerializer, description="Notification details"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Notification not found"),
        },
    )
    def get(self, request, pk):
        notification = self.get_object(pk)
        if not notification:
            return success_response(
                {"message": "Notification not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Mark as read when viewed
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        
        return success_response(NotificationSerializer(notification).data)

    @extend_schema(
        tags=["Notifications"],
        summary="Delete notification",
        description="Delete a specific notification.",
        responses={
            200: OpenApiResponse(description="Notification deleted"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Notification not found"),
        },
    )
    def delete(self, request, pk):
        notification = self.get_object(pk)
        if not notification:
            return success_response(
                {"message": "Notification not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        notification.delete()
        return success_response({"message": "Notification deleted"})


class RegisterDeviceTokenView(APIView):
    """
    Register an FCM device token for push notifications.

    Should be called on app startup and whenever the FCM token refreshes.
    If the token already exists under a different user (device re-login),
    it will be reassigned to the current user.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Register device token",
        description=(
            "Register an FCM device token for the current user. "
            "Call this on app login/startup and on token refresh. "
            "If the token exists under another user, it is reassigned."
        ),
        request=DeviceTokenRegisterSerializer,
        responses={
            200: OpenApiResponse(response=DeviceTokenSerializer, description="Token registered/updated"),
            201: OpenApiResponse(response=DeviceTokenSerializer, description="Token created"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        device_type = serializer.validated_data["device_type"]

        # Upsert: update if token exists (possibly under different user), create otherwise
        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "device_type": device_type,
                "is_active": True,
            },
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        action = "registered" if created else "updated"

        logger.info(
            "Device token %s for user %s (%s)",
            action,
            request.user.id,
            device_type,
        )

        return success_response(
            {
                "message": f"Device token {action} successfully",
                "device_token": DeviceTokenSerializer(device_token).data,
            },
            status_code=status_code,
        )


class DeleteDeviceTokenView(APIView):
    """
    Delete an FCM device token (e.g. on user logout).

    Removes the token from the database so the user stops receiving
    push notifications on that device.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Delete device token",
        description=(
            "Remove an FCM device token. Call this on user logout "
            "to stop push notifications on the device."
        ),
        parameters=[
            OpenApiParameter(
                "token",
                OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The FCM device token to delete.",
            )
        ],
        responses={
            200: OpenApiResponse(description="Token deleted"),
            400: OpenApiResponse(description="Token query parameter is required"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Token not found"),
        },
    )
    def delete(self, request):
        token = request.query_params.get("token")
        if not token:
            return success_response(
                {"message": "token query parameter is required"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = DeviceToken.objects.filter(
            token=token,
            user=request.user,
        ).delete()

        if deleted_count == 0:
            return success_response(
                {"message": "Device token not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info("Device token deleted for user %s", request.user.id)

        return success_response({"message": "Device token deleted successfully"})


class SendTestPushView(APIView):
    """
    Send a test push notification to the authenticated user's devices.

    Useful for verifying that the Firebase setup works end-to-end.
    Creates a real notification record AND sends an FCM push.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Notifications"],
        summary="Send test push notification",
        description=(
            "Sends a test push notification to all registered devices "
            "of the current user. Use this to verify FCM is configured "
            "and working correctly."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Test notification sent"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        from .services import notification_service

        user = request.user
        token_count = DeviceToken.objects.filter(
            user=user, is_active=True
        ).count()

        # Create notification + trigger FCM push
        notification = notification_service.create(
            user=user,
            title="🔔 Test Notification",
            message="If you see this on your device, FCM is working!",
            category="platform",
        )

        return success_response({
            "message": "Test notification sent",
            "notification_id": str(notification.id),
            "active_device_tokens": token_count,
            "note": (
                "Push was queued via Celery. "
                f"You have {token_count} active device token(s). "
                "If you don't receive it, check: "
                "1) Firebase credentials configured, "
                "2) Celery worker running, "
                "3) Device token is valid."
            ),
        })

