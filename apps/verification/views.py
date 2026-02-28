"""
Verification center views for Tramper.
User document submission and admin review.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import VerificationRequest
from .serializers import (
    VerificationSubmitSerializer,
    PhoneVerifySerializer,
    VerificationRequestSerializer,
    VerificationListSerializer,
    VerificationReviewSerializer,
)
from core.api import success_response
from core.storage import s3_storage


class VerificationSubmitView(APIView):
    """
    Submit verification documents.
    Authenticated user uploads ID card images, selfie, and ID card number.
    Accepts form-data with image files.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Verification Center"],
        summary="Submit verification documents",
        description=(
            "Submit ID card front, back, selfie with ID, ID card number, and phone number for identity verification. "
            "Accepts multipart form-data. Images are uploaded to S3."
        ),
        request=VerificationSubmitSerializer,
        responses={
            201: OpenApiResponse(response=VerificationRequestSerializer, description="Verification submitted."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def post(self, request):
        serializer = VerificationSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_card_number = serializer.validated_data["id_card_number"]
        id_card_front = serializer.validated_data["id_card_front"]
        id_card_back = serializer.validated_data["id_card_back"]
        selfie_with_id = serializer.validated_data["selfie_with_id"]
        phone_number = serializer.validated_data.get("phone_number")

        # Upload images to S3
        id_card_front_url = s3_storage.upload_image(id_card_front, folder="verification/id_front")
        id_card_back_url = s3_storage.upload_image(id_card_back, folder="verification/id_back")
        selfie_with_id_url = s3_storage.upload_image(selfie_with_id, folder="verification/selfie")

        # Create or update verification request
        verification, created = VerificationRequest.objects.update_or_create(
            user=request.user,
            defaults={
                "id_card_number": id_card_number,
                "id_card_front_url": id_card_front_url,
                "id_card_back_url": id_card_back_url,
                "selfie_with_id_url": selfie_with_id_url,
                "phone_number": phone_number,
                "status": "pending",  # Reset to pending on re-submission
            }
        )

        return success_response(
            VerificationRequestSerializer(verification).data,
            status_code=status.HTTP_201_CREATED,
        )


class PhoneVerifyView(APIView):
    """
    Submit phone number for verification.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Verification Center"],
        summary="Submit phone number for verification",
        description="Submit phone number to be verified by admin in the verification center.",
        request=PhoneVerifySerializer,
        responses={
            200: OpenApiResponse(response=VerificationRequestSerializer, description="Phone number submitted."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Not authenticated."),
        },
    )
    def post(self, request):
        serializer = PhoneVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]

        # Create or update verification request with phone number
        verification, created = VerificationRequest.objects.update_or_create(
            user=request.user,
            defaults={
                "phone_number": phone_number,
            }
        )

        return success_response(VerificationRequestSerializer(verification).data)

    @extend_schema(
        tags=["Verification Center"],
        summary="Get my verification status",
        description="Get the current user's latest verification request.",
        responses={
            200: OpenApiResponse(response=VerificationRequestSerializer, description="Verification request data."),
            401: OpenApiResponse(description="Not authenticated."),
            404: OpenApiResponse(description="No verification request found."),
        },
    )
    def get(self, request):
        verification = (
            VerificationRequest.objects
            .filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        if not verification:
            from rest_framework.exceptions import NotFound
            raise NotFound("No verification request found.")
        return success_response(VerificationRequestSerializer(verification).data)


class AdminVerificationListView(ListAPIView):
    """
    List all verification requests (admin only).
    """
    permission_classes = [IsAdminUser]
    serializer_class = VerificationListSerializer
    queryset = VerificationRequest.objects.select_related("user").all().order_by("-created_at")
    search_fields = ["user__email", "user__username", "user__full_name", "phone_number"]
    filterset_fields = ["status"]

    @extend_schema(
        tags=["Verification Center"],
        summary="List all verification requests (admin)",
        description="Get all verification requests. Admin only.",
        responses={
            200: OpenApiResponse(response=VerificationListSerializer(many=True), description="List of verification requests."),
            401: OpenApiResponse(description="Not authenticated."),
            403: OpenApiResponse(description="Not authorized (admin only)."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminVerificationDetailView(APIView):
    """
    Get or review a specific verification request (admin only).
    GET: View full verification request details.
    PATCH: Approve or reject verification.
    """
    permission_classes = [IsAdminUser]

    def get_object(self, pk):
        try:
            return VerificationRequest.objects.select_related("user").get(pk=pk)
        except VerificationRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Verification request not found.")

    @extend_schema(
        tags=["Verification Center"],
        summary="Get verification request detail (admin)",
        description="Get full details of a verification request. Admin only.",
        responses={
            200: OpenApiResponse(response=VerificationRequestSerializer, description="Verification request details."),
            401: OpenApiResponse(description="Not authenticated."),
            403: OpenApiResponse(description="Not authorized (admin only)."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def get(self, request, pk):
        verification = self.get_object(pk)
        return success_response(VerificationRequestSerializer(verification).data)

    @extend_schema(
        tags=["Verification Center"],
        summary="Review verification request (admin)",
        description=(
            "Approve or reject a verification request. "
            "If approved, the user's is_user_verified flag is set to True."
        ),
        request=VerificationReviewSerializer,
        responses={
            200: OpenApiResponse(response=VerificationRequestSerializer, description="Verification reviewed."),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Not authenticated."),
            403: OpenApiResponse(description="Not authorized (admin only)."),
            404: OpenApiResponse(description="Not found."),
        },
    )
    def patch(self, request, pk):
        verification = self.get_object(pk)

        serializer = VerificationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        admin_notes = serializer.validated_data.get("admin_notes", "")

        verification.status = new_status
        verification.admin_notes = admin_notes
        verification.reviewed_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save()

        # If approved, set user's is_user_verified flag to True
        if new_status == "approved":
            user = verification.user
            user.is_user_verified = True
            user.save(update_fields=["is_user_verified"])

        # If rejected, ensure flag stays False
        if new_status == "rejected":
            user = verification.user
            user.is_user_verified = False
            user.save(update_fields=["is_user_verified"])

        return success_response(VerificationRequestSerializer(verification).data)
