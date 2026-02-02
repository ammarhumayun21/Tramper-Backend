"""
Custom exception handling for REST API.
Provides consistent error response format across the application.
"""

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
)


def _normalize_errors(detail):
    """
    Normalize error details into a consistent format.
    Handles dict, list, and ErrorDetail objects from DRF and simplejwt.
    """
    if isinstance(detail, dict):
        normalized = {}
        for field, msgs in detail.items():
            if isinstance(msgs, list):
                # Take first error message from list
                normalized[field] = str(msgs[0])
            elif isinstance(msgs, dict):
                # Handle nested dict (e.g., from simplejwt TokenError)
                # Extract 'detail' or 'message' if present, otherwise use first value
                if 'detail' in msgs:
                    normalized[field] = str(msgs['detail'])
                elif 'message' in msgs:
                    normalized[field] = str(msgs['message'])
                else:
                    # Get first value from dict
                    first_value = next(iter(msgs.values()), msgs)
                    normalized[field] = str(first_value)
            else:
                normalized[field] = str(msgs)
        return normalized
    if isinstance(detail, list):
        return {"non_field_errors": str(detail[0])}
    return {"non_field_errors": str(detail)}


def custom_exception_handler(exc, context):
    """
    Custom exception handler that ensures all API errors follow the standard format:
    {"success": false, "errors": {"field": "message"}}
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Normalize all error responses to consistent format
        if hasattr(response, 'data'):
            # If response.data is already a dict with error details
            if isinstance(response.data, dict):
                response.data = {
                    "success": False,
                    "errors": _normalize_errors(response.data),
                }
            elif isinstance(response.data, list):
                response.data = {
                    "success": False,
                    "errors": {"non_field_errors": str(response.data[0])},
                }
            else:
                response.data = {
                    "success": False,
                    "errors": {"non_field_errors": str(response.data)},
                }
        return response

    return Response(
        {
            "success": False,
            "errors": {"non_field_errors": "Internal server error."},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
