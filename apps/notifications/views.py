"""
Notification views for Tramper.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Notification
from .serializers import NotificationSerializer, NotificationMarkReadSerializer
from core.api import success_response


class MyNotificationsView(ListAPIView):
    """
    List current user's notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get notifications for current user."""
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
