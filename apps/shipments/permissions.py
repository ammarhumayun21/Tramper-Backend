"""
Permissions for shipments.
"""

from rest_framework import permissions


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Anyone can read (GET)
    - Only owner or admin can update/delete
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner or admin
        return obj.sender == request.user or request.user.is_staff
