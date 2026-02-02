"""
ASGI config for tramper project.
Exposes the ASGI callable as a module-level variable named ``application``.
Used by Daphne for WebSocket support.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
