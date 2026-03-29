"""
Ziina API service for Tramper.
Handles communication with Ziina Payment Intent and Transfer APIs.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ZiinaService:
    """Service class for interacting with the Ziina API."""

    def __init__(self):
        self.base_url = getattr(settings, "ZIINA_BASE_URL", "https://api-v2.ziina.com/api")
        self.token = getattr(settings, "ZIINA_TOKEN", "")
        self.test_mode = getattr(settings, "ZIINA_TEST_MODE", False)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_payment_intent(self, amount, currency_code):
        """
        Create a Ziina Payment Intent.

        Args:
            amount: Amount in smallest currency units (e.g., fils for AED).
            currency_code: Currency code (e.g., 'AED').

        Returns:
            dict: Ziina API response with payment_intent_id and redirect_url.

        Raises:
            ZiinaAPIError: If the API call fails.
        """
        import os

        url = f"{self.base_url}/payment_intent"

        # Build redirect URLs from environment settings
        success_url = getattr(settings, "ZIINA_SUCCESS_URL", "") or os.environ.get("ZIINA_SUCCESS_URL", "")
        cancel_url = getattr(settings, "ZIINA_CANCLE_URL", "") or os.environ.get("ZIINA_CANCLE_URL", "")
        failure_url = getattr(settings, "ZIINA_FALIURE_URL", "") or os.environ.get("ZIINA_FALIURE_URL", "")

        payload = {
            "amount": int(amount),
            "currency_code": currency_code,
            "test": self.test_mode,
        }

        # Add redirect URLs if configured
        if success_url:
            payload["success_url"] = success_url
        if cancel_url:
            payload["cancel_url"] = cancel_url
        if failure_url:
            payload["failure_url"] = failure_url

        logger.info(
            "Creating Ziina payment intent: amount=%s, currency=%s",
            amount,
            currency_code,
        )

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Ziina payment intent created: id=%s",
                data.get("id"),
            )
            return data
        except requests.exceptions.RequestException as e:
            logger.error("Failed to create Ziina payment intent: %s", str(e))
            raise ZiinaAPIError(f"Failed to create payment intent: {str(e)}") from e

    def get_payment_status(self, payment_intent_id):
        """
        Get the status of a Ziina Payment Intent.

        Args:
            payment_intent_id: The Ziina payment intent ID.

        Returns:
            dict: Ziina API response with current status.

        Raises:
            ZiinaAPIError: If the API call fails.
        """
        url = f"{self.base_url}/payment_intent/{payment_intent_id}"

        logger.info("Checking Ziina payment status: id=%s", payment_intent_id)

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(
                "Ziina payment status: id=%s, status=%s",
                payment_intent_id,
                data.get("status"),
            )
            return data
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to get Ziina payment status for %s: %s",
                payment_intent_id,
                str(e),
            )
            raise ZiinaAPIError(f"Failed to get payment status: {str(e)}") from e

    def transfer_to_user(self, to_ziinames, amount, currency_code, operation_id):
        """
        Transfer funds to a user via Ziina Transfer API.

        Args:
            to_ziinames: List of Ziina usernames to transfer to.
            amount: Amount in smallest currency units.
            currency_code: Currency code (e.g., 'AED').
            operation_id: Unique UUID for this operation (idempotency key).

        Returns:
            dict: Ziina API response.

        Raises:
            ZiinaAPIError: If the API call fails.
        """
        url = f"{self.base_url}/transfer"
        payload = {
            "to_ziinames": to_ziinames if isinstance(to_ziinames, list) else [to_ziinames],
            "amount": int(amount),
            "currency_code": currency_code,
            "operation_id": str(operation_id),
        }

        logger.info(
            "Creating Ziina transfer: to=%s, amount=%s, currency=%s, operation_id=%s",
            to_ziinames,
            amount,
            currency_code,
            operation_id,
        )

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info("Ziina transfer successful: operation_id=%s", operation_id)
            return data
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to create Ziina transfer: %s",
                str(e),
            )
            raise ZiinaAPIError(f"Failed to create transfer: {str(e)}") from e


class ZiinaAPIError(Exception):
    """Custom exception for Ziina API errors."""

    pass
