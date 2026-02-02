"""
Permission classes for API authorization.
Implements role-based access control (RBAC).
"""

from rest_framework.permissions import BasePermission, IsAuthenticated
from django.utils.translation import gettext_lazy as _


class IsAdmin(IsAuthenticated):
    """
    Allow access only to admin users.
    """

    message = _("Only administrators can access this resource.")

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_staff


class IsOwner(BasePermission):
    """
    Allow access only if user is the object owner.
    Requires object to have 'owner' or 'user' attribute.
    """

    message = _("You do not have permission to access this resource.")

    def has_object_permission(self, request, view, obj):
        # Check if object has owner or user attribute
        owner_field = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner_field == request.user


class IsOwnerOrReadOnly(BasePermission):
    """
    Allow owner to edit, others can only read.
    """

    message = _("You do not have permission to modify this resource.")

    def has_object_permission(self, request, view, obj):
        # Allow read methods for any request
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Write access only to owner
        owner_field = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner_field == request.user
