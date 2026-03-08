from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.api import success_response
from core.emails import send_new_complaint_admin_email
from .models import Complaint
from .serializers import ComplaintSerializer


class ComplaintListCreateView(APIView):
    """User can list their complaints and create new ones."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Complaints"],
        summary="List my complaints",
        description="Returns all complaints for the authenticated user.",
    )
    def get(self, request):
        complaints = Complaint.objects.filter(user=request.user)
        serializer = ComplaintSerializer(complaints, many=True)
        return success_response(serializer.data)

    @extend_schema(
        tags=["Complaints"],
        summary="Create a complaint",
        description="Create a new complaint.",
        request=ComplaintSerializer,
    )
    def post(self, request):
        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save(user=request.user)

        # Notify all super admins about the new complaint
        send_new_complaint_admin_email(complaint)

        return success_response(serializer.data, status_code=status.HTTP_201_CREATED)
