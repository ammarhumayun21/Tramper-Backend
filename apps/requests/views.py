"""
Request views for Tramper.
Handles requests between users for shipments and trips.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Q

from .models import Request, CounterOffer
from .serializers import (
    RequestSerializer,
    RequestListSerializer,
    RequestCreateSerializer,
    RequestUpdateSerializer,
    CounterOfferSerializer,
    CounterOfferCreateSerializer,
)
from .permissions import IsRequestParticipant, IsSenderOrSuperuser
from core.api import success_response
from apps.notifications.services import notification_service


class MyRequestsView(ListAPIView):
    """
    List current user's requests (sent or received).
    """
    serializer_class = RequestListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        """Get requests where user is sender or receiver."""
        # Handle swagger schema generation
        if getattr(self, "swagger_fake_view", False):
            return Request.objects.none()
        
        user = self.request.user
        request_type = self.request.query_params.get("type", "all")
        
        queryset = Request.objects.select_related(
            "sender", "receiver", "shipment", "trip"
        ).prefetch_related("counter_offers")
        
        if request_type == "sent":
            queryset = queryset.filter(sender=user)
        elif request_type == "received":
            queryset = queryset.filter(receiver=user)
        else:
            queryset = queryset.filter(Q(sender=user) | Q(receiver=user))
        
        return queryset.order_by("-created_at")

    @extend_schema(
        tags=["Requests"],
        summary="Get my requests",
        description="Get all requests where current user is sender or receiver.",
        parameters=[
            OpenApiParameter("type", OpenApiTypes.STR, description="Filter: 'sent', 'received', or 'all' (default)"),
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status"),
        ],
        responses={
            200: OpenApiResponse(response=RequestListSerializer(many=True), description="List of requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RequestListCreateView(APIView):
    """
    Create a new request.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Requests"],
        summary="Create a new request",
        description="Send a request to another user for a shipment or trip.",
        request=RequestCreateSerializer,
        responses={
            201: OpenApiResponse(response=RequestSerializer, description="Request created successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = RequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        req = serializer.save(sender=request.user)
        
        # Send notification to receiver
        notification_service.notify_request_created(req)
        
        return success_response(
            RequestSerializer(req).data,
            status_code=status.HTTP_201_CREATED,
        )


class RequestDetailView(APIView):
    """
    Retrieve or update a request.
    """
    permission_classes = [IsAuthenticated, IsRequestParticipant]

    def get_object(self, pk):
        """Get request by ID."""
        try:
            req = Request.objects.select_related(
                "sender", "receiver", "shipment", "trip"
            ).prefetch_related(
                "counter_offers__sender", "counter_offers__receiver",
                "shipment__items"
            ).get(pk=pk)
            self.check_object_permissions(self.request, req)
            return req
        except Request.DoesNotExist:
            return None

    @extend_schema(
        tags=["Requests"],
        summary="Get request details",
        description="Retrieve detailed information about a specific request.",
        responses={
            200: OpenApiResponse(response=RequestSerializer, description="Request details"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Request not found"),
        },
    )
    def get(self, request, pk):
        req = self.get_object(pk)
        if not req:
            return success_response(
                {"message": "Request not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(RequestSerializer(req).data)

    @extend_schema(
        tags=["Requests"],
        summary="Update request status",
        description="Update request status (accept, reject, cancel).",
        request=RequestUpdateSerializer,
        responses={
            200: OpenApiResponse(response=RequestSerializer, description="Request updated successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Request not found"),
        },
    )
    def patch(self, request, pk):
        req = self.get_object(pk)
        if not req:
            return success_response(
                {"message": "Request not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        old_status = req.status
        serializer = RequestUpdateSerializer(req, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Send notifications based on status change
        if req.status != old_status:
            if req.status == "accepted":
                notification_service.notify_request_accepted(req)
            elif req.status == "rejected":
                notification_service.notify_request_rejected(req)
        
        # If accepted, update shipment traveler
        if req.status == "accepted" and req.shipment:
            if req.sender == req.shipment.sender:
                # Shipment owner accepted traveler's offer
                req.shipment.traveler = req.receiver
            else:
                # Traveler's offer was accepted by shipment owner
                req.shipment.traveler = req.sender
            req.shipment.status = "accepted"
            req.shipment.save(update_fields=["traveler", "status"])
        
        return success_response(RequestSerializer(req).data)

    @extend_schema(
        tags=["Requests"],
        summary="Delete a request",
        description="Delete a request. Only the sender (creator) or a superuser can delete.",
        responses={
            200: OpenApiResponse(description="Request deleted successfully"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied - only sender or superuser can delete"),
            404: OpenApiResponse(description="Request not found"),
        },
    )
    def delete(self, request, pk):
        try:
            req = Request.objects.get(pk=pk)
        except Request.DoesNotExist:
            return success_response(
                {"message": "Request not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if user is sender or superuser
        if req.sender != request.user and not request.user.is_superuser:
            return success_response(
                {"message": "Only the request creator or a superuser can delete this request"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        req.delete()
        return success_response({"message": "Request deleted successfully"})


class CounterOfferCreateView(APIView):
    """
    Create a counter offer for a request.
    """
    permission_classes = [IsAuthenticated]

    def get_request_object(self, pk):
        """Get request by ID."""
        try:
            return Request.objects.select_related("sender", "receiver").get(pk=pk)
        except Request.DoesNotExist:
            return None

    @extend_schema(
        tags=["Requests"],
        summary="Create counter offer",
        description="Create a counter offer for a request. Only participants can counter.",
        request=CounterOfferCreateSerializer,
        responses={
            201: OpenApiResponse(response=RequestSerializer, description="Counter offer created"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Request not found"),
        },
    )
    def post(self, request, pk):
        req = self.get_request_object(pk)
        if not req:
            return success_response(
                {"message": "Request not found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if user is participant
        if request.user != req.sender and request.user != req.receiver:
            return success_response(
                {"message": "Permission denied"},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Check if request is in valid state for counter offer
        if req.status not in ["pending", "countered"]:
            return success_response(
                {"message": "Cannot counter offer on this request"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = CounterOfferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Determine receiver of counter offer
        if request.user == req.sender:
            counter_receiver = req.receiver
        else:
            counter_receiver = req.sender
        
        # Create counter offer
        counter_offer = CounterOffer.objects.create(
            request=req,
            sender=request.user,
            receiver=counter_receiver,
            **serializer.validated_data
        )
        
        # Send notification to receiver of counter offer
        notification_service.notify_counter_offer(counter_offer)
        
        # Update request status
        req.status = "countered"
        req.save(update_fields=["status", "updated_at"])
        
        return success_response(
            RequestSerializer(req).data,
            status_code=status.HTTP_201_CREATED,
        )


class ShipmentRequestsView(ListAPIView):
    """
    List all requests for a specific shipment.
    """
    serializer_class = RequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get requests for shipment."""
        shipment_id = self.kwargs.get("shipment_id")
        return Request.objects.select_related(
            "sender", "receiver", "shipment", "trip"
        ).filter(shipment_id=shipment_id).order_by("-created_at")

    @extend_schema(
        tags=["Requests"],
        summary="Get shipment requests",
        description="Get all requests for a specific shipment.",
        responses={
            200: OpenApiResponse(response=RequestListSerializer(many=True), description="List of requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TripRequestsView(ListAPIView):
    """
    List all requests for a specific trip.
    """
    serializer_class = RequestListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get requests for trip."""
        trip_id = self.kwargs.get("trip_id")
        return Request.objects.select_related(
            "sender", "receiver", "shipment", "trip"
        ).filter(trip_id=trip_id).order_by("-created_at")

    @extend_schema(
        tags=["Requests"],
        summary="Get trip requests",
        description="Get all requests for a specific trip.",
        responses={
            200: OpenApiResponse(response=RequestListSerializer(many=True), description="List of requests"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
