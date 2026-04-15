"""
FCM Push notification service — reusable methods callable from anywhere in the backend.

Public API (import and call from views, services, signals, etc.):
    send_to_user(user, title, body, data=None)   — push to all devices of a user (async)
    send_to_users(users, title, body, data=None)  — push to multiple users (async)
    send_to_token(token, title, body, data=None)  — push to a specific token (sync)
    send_to_topic(topic, title, body, data=None)  — push to a topic (sync)

All methods are safe to call even if Firebase is not configured — they log a warning
and return silently.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from celery import shared_task

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery tasks (async, runs in the worker process)
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=5, ignore_result=True)
def send_push_to_user_task(self, user_id: str, title: str, body: str, data: Optional[dict] = None):
    """
    Celery task: send FCM push to all active devices of a single user.
    Automatically cleans up invalid/expired tokens.
    """
    from apps.notifications.firebase import get_messaging
    from apps.notifications.models import DeviceToken

    messaging = get_messaging()
    if messaging is None:
        logger.warning("Firebase not configured — skipping push for user %s", user_id)
        return

    tokens = list(
        DeviceToken.objects.filter(user_id=user_id, is_active=True)
        .values_list("token", flat=True)
    )

    if not tokens:
        logger.debug("No active device tokens for user %s", user_id)
        return

    _send_to_tokens(messaging, tokens, title, body, data)


@shared_task(bind=True, max_retries=3, default_retry_delay=5, ignore_result=True)
def send_push_to_users_task(self, user_ids: list[str], title: str, body: str, data: Optional[dict] = None):
    """
    Celery task: send FCM push to all active devices of multiple users.
    Uses batch sending (500 per batch, FCM limit).
    """
    from apps.notifications.firebase import get_messaging
    from apps.notifications.models import DeviceToken

    messaging = get_messaging()
    if messaging is None:
        logger.warning("Firebase not configured — skipping push for %d users", len(user_ids))
        return

    tokens = list(
        DeviceToken.objects.filter(user_id__in=user_ids, is_active=True)
        .values_list("token", flat=True)
    )

    if not tokens:
        logger.debug("No active device tokens for users %s", user_ids)
        return

    _send_to_tokens(messaging, tokens, title, body, data)


# ---------------------------------------------------------------------------
# Public convenience wrappers (what you import and call)
# ---------------------------------------------------------------------------


def send_to_user(user, title: str, body: str, data: Optional[dict[str, Any]] = None) -> None:
    """
    Queue an async push notification to all devices of a single user.

    Usage:
        from apps.notifications.push import send_to_user
        send_to_user(user, "Title", "Body text", data={"key": "value"})
    """
    try:
        # Ensure data values are strings (FCM requirement)
        safe_data = _sanitize_data(data)
        send_push_to_user_task.delay(str(user.id), title, body, safe_data)
    except Exception:
        logger.exception("Failed to queue push task for user %s", user)


def send_to_users(users, title: str, body: str, data: Optional[dict[str, Any]] = None) -> None:
    """
    Queue an async push notification to multiple users.

    Accepts a queryset, list of User objects, or list of user ID strings.

    Usage:
        from apps.notifications.push import send_to_users
        send_to_users(User.objects.filter(is_active=True), "Title", "Body")
    """
    try:
        user_ids = [str(u.id) if hasattr(u, "id") else str(u) for u in users]
        if not user_ids:
            return
        safe_data = _sanitize_data(data)
        send_push_to_users_task.delay(user_ids, title, body, safe_data)
    except Exception:
        logger.exception("Failed to queue push task for multiple users")


def send_to_token(token: str, title: str, body: str, data: Optional[dict[str, Any]] = None) -> bool:
    """
    Send a push notification to a specific FCM token (synchronous).

    Returns True on success, False on failure.
    Automatically deactivates invalid tokens.
    """
    from apps.notifications.firebase import get_messaging

    messaging = get_messaging()
    if messaging is None:
        logger.warning("Firebase not configured — skipping push to token")
        return False

    safe_data = _sanitize_data(data)

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=safe_data or {},
        token=token,
    )

    try:
        messaging.send(message)
        logger.info("Push sent to token %s...%s", token[:8], token[-4:])
        return True
    except messaging.UnregisteredError:
        logger.info("Token unregistered, deactivating: %s...%s", token[:8], token[-4:])
        _cleanup_invalid_tokens([token])
        return False
    except messaging.InvalidArgumentError:
        logger.warning("Invalid token, deactivating: %s...%s", token[:8], token[-4:])
        _cleanup_invalid_tokens([token])
        return False
    except Exception:
        logger.exception("Failed to send push to token %s...%s", token[:8], token[-4:])
        return False


def send_to_topic(topic: str, title: str, body: str, data: Optional[dict[str, Any]] = None) -> bool:
    """
    Send a push notification to an FCM topic (synchronous).

    Returns True on success, False on failure.
    """
    from apps.notifications.firebase import get_messaging

    messaging = get_messaging()
    if messaging is None:
        logger.warning("Firebase not configured — skipping push to topic '%s'", topic)
        return False

    safe_data = _sanitize_data(data)

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=safe_data or {},
        topic=topic,
    )

    try:
        messaging.send(message)
        logger.info("Push sent to topic '%s'", topic)
        return True
    except Exception:
        logger.exception("Failed to send push to topic '%s'", topic)
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _send_to_tokens(messaging, tokens: list[str], title: str, body: str, data: Optional[dict] = None) -> int:
    """
    Send FCM push to a list of tokens using batch API.
    Returns the number of successful sends.
    Automatically cleans up invalid tokens.
    """
    safe_data = _sanitize_data(data)
    successful = 0
    invalid_tokens = []

    # FCM send_each supports up to 500 messages per call
    batch_size = 500
    for i in range(0, len(tokens), batch_size):
        batch_tokens = tokens[i : i + batch_size]

        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=safe_data or {},
                token=token,
            )
            for token in batch_tokens
        ]

        try:
            response = messaging.send_each(messages)

            for idx, send_response in enumerate(response.responses):
                if send_response.success:
                    successful += 1
                else:
                    exception = send_response.exception
                    token = batch_tokens[idx]
                    if _is_token_invalid(exception):
                        invalid_tokens.append(token)
                        logger.info(
                            "Invalid/expired token detected: %s...%s",
                            token[:8],
                            token[-4:],
                        )
                    else:
                        logger.warning(
                            "Failed to send push to token %s...%s: %s",
                            token[:8],
                            token[-4:],
                            exception,
                        )

        except Exception:
            logger.exception("Batch send failed for %d tokens", len(batch_tokens))

    # Clean up invalid tokens
    if invalid_tokens:
        cleaned = _cleanup_invalid_tokens(invalid_tokens)
        logger.info("Cleaned up %d invalid tokens", cleaned)

    logger.info(
        "Push batch complete: %d/%d successful, %d invalid tokens removed",
        successful,
        len(tokens),
        len(invalid_tokens),
    )
    return successful


def _is_token_invalid(exception) -> bool:
    """Check if an FCM exception indicates the token is permanently invalid."""
    from firebase_admin import exceptions as fb_exceptions
    from firebase_admin.messaging import UnregisteredError

    if isinstance(exception, UnregisteredError):
        return True

    # Check for INVALID_ARGUMENT or NOT_FOUND error codes
    if isinstance(exception, fb_exceptions.InvalidArgumentError):
        return True
    if isinstance(exception, fb_exceptions.NotFoundError):
        return True

    return False


def _cleanup_invalid_tokens(invalid_tokens: list[str]) -> int:
    """Deactivate invalid device tokens from the database."""
    from apps.notifications.models import DeviceToken

    return DeviceToken.objects.filter(token__in=invalid_tokens).update(is_active=False)


def _sanitize_data(data: Optional[dict]) -> Optional[dict]:
    """Convert all data values to strings (FCM requirement)."""
    if not data:
        return data
    return {str(k): str(v) for k, v in data.items() if v is not None}
