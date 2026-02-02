"""
Example middleware for custom functionality.
"""

from django.utils.deprecation import MiddlewareMixin


class APIVersionMiddleware(MiddlewareMixin):
    """
    Custom middleware to track API version usage.
    """

    def process_request(self, request):
        """Extract and store API version from request."""
        path = request.path
        if "/api/v" in path:
            # Extract version number
            parts = path.split("/api/v")
            if len(parts) > 1:
                version = parts[1].split("/")[0]
                request.api_version = f"v{version}"
        return None
