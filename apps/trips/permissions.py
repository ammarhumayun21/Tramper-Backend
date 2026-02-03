"""
Custom permissions for trips.
"""

from rest_framework import permissions


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow:
    - Admins to do anything
    - Owners to edit/delete their own trips
    - Authenticated users to create trips
    - Anyone to read trips
    """

    def has_permission(self, request, view):
        # Allow read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow authenticated users to create
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admin can do anything
        if request.user and request.user.is_staff:
            return True

        # Write permissions are only allowed to the owner
        return obj.traveler == request.user
