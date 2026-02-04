"""
Permissions for requests.
"""

from rest_framework import permissions


class IsRequestParticipant(permissions.BasePermission):
    """
    Custom permission:
    - Only sender or receiver can view/modify request
    - Superusers have access
    """

    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user or obj.receiver == request.user or request.user.is_superuser


class IsSenderOrSuperuser(permissions.BasePermission):
    """
    Custom permission:
    - Only the sender (creator) of the request can delete it
    - Superusers can also delete
    """

    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user or request.user.is_superuser
