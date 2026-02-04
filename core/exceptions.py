"""
Custom exception handling for REST API.
Provides consistent error response format across the application.
"""

import logging
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

logger = logging.getLogger(__name__)


def _normalize_errors(detail, parent_field=None):
    """
    Normalize error details into a single error message string.
    Returns only the first error encountered.
    Handles dict, list, and ErrorDetail objects from DRF and simplejwt.
    Supports deeply nested errors from nested serializers.
    """
    if isinstance(detail, dict):
        # Get the first field and its error message
        first_field = next(iter(detail.keys()))
        first_msgs = detail[first_field]
        
        # Build the full field path
        if parent_field:
            full_field = f"{parent_field}.{first_field}"
        else:
            full_field = first_field
        
        if isinstance(first_msgs, list):
            if len(first_msgs) > 0:
                first_item = first_msgs[0]
                # Check if it's a nested dict (e.g., list of objects with errors)
                if isinstance(first_item, dict):
                    return _normalize_errors(first_item, full_field)
                else:
                    msg = str(first_item)
            else:
                msg = "Invalid value"
        elif isinstance(first_msgs, dict):
            # Handle nested dict (recursively)
            return _normalize_errors(first_msgs, full_field)
        else:
            msg = str(first_msgs)
        
        # Format as "field_name error message"
        if first_field == 'non_field_errors' or first_field == 'detail':
            return msg
        else:
            # Clean up the message
            msg = msg.lower() if msg and msg[0].isupper() else msg
            return f"{full_field} {msg}"
    
    if isinstance(detail, list):
        if len(detail) > 0:
            first_item = detail[0]
            if isinstance(first_item, dict):
                return _normalize_errors(first_item, parent_field)
            return str(first_item)
        return "Invalid value"
    
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

    # Log the full exception for debugging
    logger.exception("Unhandled exception in API: %s", exc, exc_info=True)
    
    return Response(
        {
            "success": False,
            "error": "Internal server error.",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
