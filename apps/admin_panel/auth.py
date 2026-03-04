"""
Cookie-based JWT authentication for admin panel.
Reads JWT from HTTP-only cookie instead of Authorization header.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the token from an HTTP-only cookie.
    Falls back to the default Authorization header if no cookie is present.
    """

    def authenticate(self, request):
        # Try cookie first
        raw_token = request.COOKIES.get("access_token")
        if raw_token:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token

        # Fall back to header-based auth
        return super().authenticate(request)
