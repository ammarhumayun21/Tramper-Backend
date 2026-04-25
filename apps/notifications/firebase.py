"""
Firebase Admin SDK singleton initialization.

Supports two credential loading strategies:
  1. FIREBASE_CREDENTIALS_JSON — Base64-encoded service account JSON (for Heroku/production)
  2. FIREBASE_CREDENTIALS_PATH — File path to service account JSON (for local development)

Usage:
    from apps.notifications.firebase import get_firebase_app
    app = get_firebase_app()  # Returns None if not configured
"""

import base64
import json
import logging

import firebase_admin
from firebase_admin import credentials, messaging  # noqa: F401
from django.conf import settings

logger = logging.getLogger(__name__)

_app = None
_initialized = False


def get_firebase_app():
    """
    Return the Firebase app instance, initializing on first call.

    Thread-safe: firebase_admin.initialize_app is protected by a global flag.
    Returns None if Firebase credentials are not configured (graceful degradation).
    """
    global _app, _initialized

    if _initialized:
        return _app

    try:
        # Option 1: Base64-encoded JSON string (Heroku production)
        creds_json = getattr(settings, "FIREBASE_CREDENTIALS_JSON", "")
        if creds_json:
            cred_dict = json.loads(base64.b64decode(creds_json))
            cred = credentials.Certificate(cred_dict)
            try:
                _app = firebase_admin.get_app()
                logger.info("Firebase Admin SDK reused existing app (base64 credentials).")
            except ValueError:
                _app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized from base64 credentials.")

        # Option 2: File path (local development)
        elif getattr(settings, "FIREBASE_CREDENTIALS_PATH", ""):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            try:
                _app = firebase_admin.get_app()
                logger.info("Firebase Admin SDK reused existing app (file: %s).", settings.FIREBASE_CREDENTIALS_PATH)
            except ValueError:
                _app = firebase_admin.initialize_app(cred)
                logger.info(
                    "Firebase Admin SDK initialized from file: %s",
                    settings.FIREBASE_CREDENTIALS_PATH,
                )

        else:
            logger.warning(
                "Firebase credentials not configured. "
                "Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH. "
                "Push notifications are DISABLED."
            )
            _app = None

    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK.")
        _app = None

    _initialized = True
    return _app


def get_messaging():
    """
    Return the firebase_admin.messaging module, ensuring the app is initialized.

    Returns None if Firebase is not configured.
    """
    app = get_firebase_app()
    if app is None:
        return None
    return messaging
