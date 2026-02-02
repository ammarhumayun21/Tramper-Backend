"""
Custom authentication backend for email-based login.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authenticate using email address instead of username.
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate user by email and password.
        
        Args:
            request: HTTP request object
            email: User's email address
            password: User's password
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        if email is None:
            email = kwargs.get("username")
        
        if email is None or password is None:
            return None
        
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            # Run the default password hasher to reduce timing attacks
            User().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

    def get_user(self, user_id):
        """
        Get user by primary key.
        
        Args:
            user_id: User's primary key (UUID)
            
        Returns:
            User object if found and active, None otherwise
        """
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None
