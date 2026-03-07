"""
Permission classes for the chatrooms app.
"""

from rest_framework.permissions import BasePermission


class IsChatParticipant(BasePermission):
    """
    Only the two chatroom participants (sender/receiver) or staff can access.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            user.id == obj.sender_id
            or user.id == obj.receiver_id
            or user.is_staff
        )
