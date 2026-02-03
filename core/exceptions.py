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
    Normalize error details into a single error message string.
    Returns only the first error encountered.
    Handles dict, list, and ErrorDetail objects from DRF and simplejwt.
    """
    if isinstance(detail, dict):
        # Get the first field and its error message
        first_field = next(iter(detail.keys()))
        first_msgs = detail[first_field]
        
        if isinstance(first_msgs, list):
            # Take first error message from list
            msg = str(first_msgs[0])
        elif isinstance(first_msgs, dict):
            # Handle nested dict (e.g., from simplejwt TokenError)
            if 'detail' in first_msgs:
                msg = str(first_msgs['detail'])
            elif 'message' in first_msgs:
                msg = str(first_msgs['message'])
            else:
                first_value = next(iter(first_msgs.values()), first_msgs)
                msg = str(first_value)
        else:
            msg = str(first_msgs)
        
        # Format as "field_name error message"
        if first_field == 'non_field_errors' or first_field == 'detail':
            return msg
        else:
            return f"{first_field} {msg.lower()}" if msg[0].isupper() else f"{first_field} {msg}"
    
    if isinstance(detail, list):
        return str(detail[0])
    
    return str(detail)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that ensures all API errors follow the standard format:
    {"success": false, "error": "field_name error message. another_field error message."}
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        # Normalize all error responses to consistent format
        if hasattr(response, 'data'):
            # If response.data is already a dict with error details
            if isinstance(response.data, dict):
                response.data = {
                    "success": False,
                    "error": _normalize_errors(response.data),
                }
            elif isinstance(response.data, list):
                response.data = {
                    "success": False,
                    "error": str(response.data[0]),
                }
            else:
                response.data = {
                    "success": False,
                    "error": str(response.data),
                }
        return response

    return Response(
        {
            "success": False,
            "error": "Internal server error.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
