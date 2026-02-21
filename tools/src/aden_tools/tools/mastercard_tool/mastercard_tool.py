"""
Mastercard Payment Tool - Payment processing via Mastercard Payment Gateway Services (MPGS).

Supports:
- REST API authentication (MASTERCARD_MERCHANT_ID + MASTERCARD_API_PASSWORD)

Use Cases:
- Tokenize card details for PCI compliance friendly storage
- Authorize payments and place holds on funds
- Capture authorized transactions
- Process direct payments
- Issue full or partial refunds
- Retrieve transaction status and details
- Verify 3D Secure authentication eligibility

API Reference: https://test-gateway.mastercard.com/api/documentation/integrationGuidelines/index.html
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

MASTERCARD_API_VERSION = "78"


class _MastercardClient:
    """Internal client wrapping Mastercard Payment Gateway API calls."""

    def __init__(self, merchant_id: str, api_password: str, base_url: str):
        self._merchant_id = merchant_id
        self._api_password = api_password
        self._base_url = base_url.rstrip("/")

    @property
    def _auth(self) -> tuple[str, str]:
        """HTTP Basic auth tuple."""
        return (f"merchant.{self._merchant_id}", self._api_password)

    def _api_url(self, path: str) -> str:
        """Construct full API URL."""
        return f"{self._base_url}/api/rest/version/{MASTERCARD_API_VERSION}/merchant/{self._merchant_id}{path}"

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid Mastercard API credentials"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions. Check your merchant account access."}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 400:
            try:
                detail = response.json().get("error", {}).get("explanation", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Bad request: {detail}"}
        if response.status_code == 429:
            return {"error": "Mastercard rate limit exceeded. Try again later."}
        if response.status_code >= 400:
            try:
                error_data = response.json().get("error", {})
                detail = error_data.get("explanation", response.text)
            except Exception:
                detail = response.text
            return {"error": f"Mastercard API error (HTTP {response.status_code}): {detail}"}
        return response.json()

    def create_token(
        self,
        card_number: str,
        card_expiry_month: str,
        card_expiry_year: str,
        card_security_code: str | None = None,
    ) -> dict[str, Any]:
        """Create a token for card details."""
        body: dict[str, Any] = {
            "sourceOfFunds": {
                "provided": {
                    "card": {
                        "number": card_number,
                        "expiry": {
                            "month": card_expiry_month,
                            "year": card_expiry_year,
                        },
                    }
                }
            }
        }

        if card_security_code:
            body["sourceOfFunds"]["provided"]["card"]["securityCode"] = card_security_code

        response = httpx.put(
            self._api_url("/token"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "token": result.get("repositoryId"),
                "status": result.get("result"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def authorize(
        self,
        order_id: str,
        amount: str,
        currency: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
        card_security_code: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Authorize a payment (place hold on funds without capturing)."""
        body: dict[str, Any] = {
            "apiOperation": "AUTHORIZE",
            "order": {
                "amount": amount,
                "currency": currency,
            },
            "transaction": {
                "type": "AUTHORIZATION",
            },
        }

        if description:
            body["order"]["description"] = description

        if token:
            body["sourceOfFunds"] = {"token": token}
        elif card_number:
            body["sourceOfFunds"] = {
                "provided": {
                    "card": {
                        "number": card_number,
                        "expiry": {
                            "month": card_expiry_month,
                            "year": card_expiry_year,
                        },
                    }
                }
            }
            if card_security_code:
                body["sourceOfFunds"]["provided"]["card"]["securityCode"] = card_security_code

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/1"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "order_id": order_id,
                "transaction_id": result.get("transaction", {}).get("id"),
                "amount": result.get("order", {}).get("totalAuthorizedAmount"),
                "currency": result.get("order", {}).get("currency"),
                "status": result.get("result"),
                "authorization_code": result.get("transaction", {}).get("authorizationCode"),
                "response_code": result.get("response", {}).get("gatewayCode"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def pay(
        self,
        order_id: str,
        amount: str,
        currency: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
        card_security_code: str | None = None,
        description: str | None = None,
        authorize_first: bool = False,
    ) -> dict[str, Any]:
        """Execute a direct payment (AUTHORIZE+CAPTURE) or capture a previously authorized transaction."""
        operation = "AUTHORIZE" if authorize_first else "AUTHORIZE_AND_CAPTURE"

        body: dict[str, Any] = {
            "apiOperation": operation,
            "order": {
                "amount": amount,
                "currency": currency,
            },
            "transaction": {
                "type": "PURCHASE" if not authorize_first else "AUTHORIZATION",
            },
        }

        if description:
            body["order"]["description"] = description

        if token:
            body["sourceOfFunds"] = {"token": token}
        elif card_number:
            body["sourceOfFunds"] = {
                "provided": {
                    "card": {
                        "number": card_number,
                        "expiry": {
                            "month": card_expiry_month,
                            "year": card_expiry_year,
                        },
                    }
                }
            }
            if card_security_code:
                body["sourceOfFunds"]["provided"]["card"]["securityCode"] = card_security_code

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/1"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "order_id": order_id,
                "transaction_id": result.get("transaction", {}).get("id"),
                "amount": result.get("order", {}).get("totalAuthorizedAmount"),
                "captured_amount": result.get("order", {}).get("totalCapturedAmount"),
                "currency": result.get("order", {}).get("currency"),
                "status": result.get("result"),
                "authorization_code": result.get("transaction", {}).get("authorizationCode"),
                "response_code": result.get("response", {}).get("gatewayCode"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def capture(
        self,
        order_id: str,
        transaction_id: str,
        amount: str | None = None,
        currency: str | None = None,
    ) -> dict[str, Any]:
        """Capture a previously authorized transaction."""
        body: dict[str, Any] = {
            "apiOperation": "CAPTURE",
            "transaction": {
                "type": "CAPTURE",
            },
        }

        if amount:
            body["order"] = {"amount": amount}
            if currency:
                body["order"]["currency"] = currency

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/{transaction_id}"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "order_id": order_id,
                "transaction_id": transaction_id,
                "amount": result.get("order", {}).get("totalCapturedAmount"),
                "currency": result.get("order", {}).get("currency"),
                "status": result.get("result"),
                "response_code": result.get("response", {}).get("gatewayCode"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def refund(
        self,
        order_id: str,
        amount: str,
        currency: str,
        transaction_id: str | None = None,
        target_transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a full or partial refund."""
        txn_id = transaction_id or str(uuid.uuid4())[:8]

        body: dict[str, Any] = {
            "apiOperation": "REFUND",
            "order": {
                "amount": amount,
                "currency": currency,
            },
            "transaction": {
                "type": "REFUND",
            },
        }

        if target_transaction_id:
            body["transaction"]["targetTransactionId"] = target_transaction_id

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/{txn_id}"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "order_id": order_id,
                "transaction_id": txn_id,
                "refund_amount": result.get("transaction", {}).get("amount"),
                "currency": result.get("order", {}).get("currency"),
                "status": result.get("result"),
                "response_code": result.get("response", {}).get("gatewayCode"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def retrieve_transaction(
        self,
        order_id: str,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve transaction status and details."""
        if transaction_id:
            response = httpx.get(
                self._api_url(f"/order/{order_id}/transaction/{transaction_id}"),
                auth=self._auth,
                timeout=30.0,
            )
            result = self._handle_response(response)

            if "error" not in result:
                return {
                    "order_id": order_id,
                    "transaction_id": result.get("transaction", {}).get("id"),
                    "type": result.get("transaction", {}).get("type"),
                    "amount": result.get("transaction", {}).get("amount"),
                    "currency": result.get("transaction", {}).get("currency"),
                    "status": result.get("transaction", {}).get("status"),
                    "authorization_code": result.get("transaction", {}).get("authorizationCode"),
                    "response_code": result.get("response", {}).get("gatewayCode"),
                    "correlation_id": result.get("correlationId"),
                }
            return result
        else:
            response = httpx.get(
                self._api_url(f"/order/{order_id}"),
                auth=self._auth,
                timeout=30.0,
            )
            result = self._handle_response(response)

            if "error" not in result:
                transactions = []
                for txn in result.get("transaction", []):
                    transactions.append(
                        {
                            "id": txn.get("id"),
                            "type": txn.get("type"),
                            "amount": txn.get("amount"),
                            "currency": txn.get("currency"),
                            "status": txn.get("status"),
                        }
                    )

                return {
                    "order_id": order_id,
                    "total_authorized_amount": result.get("order", {}).get("totalAuthorizedAmount"),
                    "total_captured_amount": result.get("order", {}).get("totalCapturedAmount"),
                    "total_refunded_amount": result.get("order", {}).get("totalRefundedAmount"),
                    "currency": result.get("order", {}).get("currency"),
                    "status": result.get("order", {}).get("status"),
                    "transactions": transactions,
                    "correlation_id": result.get("correlationId"),
                }
            return result

    def verify_service(
        self,
        order_id: str,
        transaction_id: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
    ) -> dict[str, Any]:
        """Verify 3D Secure authentication eligibility (check card enrollment)."""
        body: dict[str, Any] = {
            "apiOperation": "CHECK_3DS_ENROLLMENT",
            "order": {
                "amount": "0",
                "currency": "USD",
            },
            "transaction": {
                "type": "VERIFY",
            },
        }

        if token:
            body["sourceOfFunds"] = {"token": token}
        elif card_number:
            body["sourceOfFunds"] = {
                "provided": {
                    "card": {
                        "number": card_number,
                        "expiry": {
                            "month": card_expiry_month,
                            "year": card_expiry_year,
                        },
                    }
                }
            }

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/{transaction_id}"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            secure_id = result.get("3DS", {}).get("secureId")
            enrolled = result.get("3DS", {}).get("enrolled")

            return {
                "order_id": order_id,
                "transaction_id": transaction_id,
                "secure_id": secure_id,
                "enrolled": enrolled,
                "acs_url": result.get("3DS", {}).get("acsUrl"),
                "payer_authentication_request": result.get("3DS", {}).get(
                    "payerAuthenticationRequest"
                ),
                "status": result.get("result"),
                "correlation_id": result.get("correlationId"),
            }
        return result

    def void(
        self,
        order_id: str,
        transaction_id: str,
        target_transaction_id: str,
    ) -> dict[str, Any]:
        """Void a previously authorized transaction."""
        body: dict[str, Any] = {
            "apiOperation": "VOID",
            "transaction": {
                "type": "VOID",
                "targetTransactionId": target_transaction_id,
            },
        }

        response = httpx.put(
            self._api_url(f"/order/{order_id}/transaction/{transaction_id}"),
            auth=self._auth,
            json=body,
            timeout=30.0,
        )
        result = self._handle_response(response)

        if "error" not in result:
            return {
                "order_id": order_id,
                "transaction_id": transaction_id,
                "voided_transaction_id": target_transaction_id,
                "status": result.get("result"),
                "response_code": result.get("response", {}).get("gatewayCode"),
                "correlation_id": result.get("correlationId"),
            }
        return result


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Mastercard payment tools with the MCP server."""

    def _get_credentials() -> tuple[str, str, str] | dict[str, str]:
        """Get Mastercard credentials from credential manager or environment."""
        if credentials is not None:
            merchant_id = credentials.get("mastercard_merchant_id")
            api_password = credentials.get("mastercard_api_password")
            base_url = credentials.get("mastercard_base_url")

            if merchant_id is not None and not isinstance(merchant_id, str):
                merchant_id = None
            if api_password is not None and not isinstance(api_password, str):
                api_password = None
            if base_url is not None and not isinstance(base_url, str):
                base_url = None

            if merchant_id and api_password:
                url = base_url or "https://test-gateway.mastercard.com"
                return merchant_id, api_password, url
        else:
            merchant_id = os.getenv("MASTERCARD_MERCHANT_ID")
            api_password = os.getenv("MASTERCARD_API_PASSWORD")
            base_url = os.getenv("MASTERCARD_BASE_URL")

            if merchant_id and api_password:
                url = base_url or "https://test-gateway.mastercard.com"
                return merchant_id, api_password, url

        return {
            "error": "Mastercard credentials not configured",
            "help": (
                "Set MASTERCARD_MERCHANT_ID and MASTERCARD_API_PASSWORD environment variables. "
                "Get your credentials from your Mastercard Payment Gateway provider. "
                "Optionally set MASTERCARD_BASE_URL for custom gateway endpoints."
            ),
        }

    def _get_client() -> _MastercardClient | dict[str, str]:
        """Get a Mastercard client, or return an error dict if no credentials."""
        creds = _get_credentials()
        if isinstance(creds, dict):
            return creds
        return _MastercardClient(creds[0], creds[1], creds[2])

    @mcp.tool()
    def mastercard_create_token(
        card_number: str,
        card_expiry_month: str,
        card_expiry_year: str,
        card_security_code: str | None = None,
    ) -> dict:
        """
        Create a secure token for card details.

        Tokens allow you to store card information securely without handling
        sensitive data directly, improving PCI compliance.

        Args:
            card_number: The card number (PAN)
            card_expiry_month: Two-digit expiry month (e.g., "05")
            card_expiry_year: Four-digit expiry year (e.g., "2027")
            card_security_code: Optional card security code (CVV/CVC)

        Returns:
            Dict with token details or error

        Example:
            mastercard_create_token(
                card_number="5123456789012346",
                card_expiry_month="05",
                card_expiry_year="2027"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not card_number or len(card_number) < 13:
            return {"error": "Invalid card number"}
        if not card_expiry_month or len(card_expiry_month) != 2:
            return {"error": "Expiry month must be 2 digits (e.g., '05')"}
        if not card_expiry_year or len(card_expiry_year) != 4:
            return {"error": "Expiry year must be 4 digits (e.g., '2027')"}

        try:
            return client.create_token(
                card_number, card_expiry_month, card_expiry_year, card_security_code
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_authorize(
        order_id: str,
        amount: str,
        currency: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
        card_security_code: str | None = None,
        description: str | None = None,
    ) -> dict:
        """
        Authorize a payment (verify funds and place hold).

        This verifies that funds are available and places a hold on the amount
        without capturing it. Use mastercard_capture to capture the funds later.

        Args:
            order_id: Unique identifier for this order
            amount: Amount to authorize in smallest currency unit (e.g., cents)
            currency: ISO 4217 currency code (e.g., "USD", "EUR")
            token: Previously created token (recommended)
            card_number: Card number (if not using token)
            card_expiry_month: Card expiry month (if not using token)
            card_expiry_year: Card expiry year (if not using token)
            card_security_code: Card security code (if not using token)
            description: Optional order description

        Returns:
            Dict with authorization details or error

        Example:
            mastercard_authorize(
                order_id="order-123",
                amount="1000",
                currency="USD",
                token="1234567890123456"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not amount:
            return {"error": "amount is required"}
        if not currency or len(currency) != 3:
            return {"error": "currency must be a 3-letter code (e.g., USD)"}

        if not token and not card_number:
            return {"error": "Either token or card details must be provided"}

        if card_number and (not card_expiry_month or not card_expiry_year):
            return {"error": "Card expiry month and year required when using card number"}

        try:
            return client.authorize(
                order_id,
                amount,
                currency,
                token,
                card_number,
                card_expiry_month,
                card_expiry_year,
                card_security_code,
                description,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_pay(
        order_id: str,
        amount: str,
        currency: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
        card_security_code: str | None = None,
        description: str | None = None,
        authorize_first: bool = False,
    ) -> dict:
        """
        Execute a direct payment (authorize and capture immediately).

        This processes a payment in one step, authorizing and capturing funds
        in a single transaction.

        Args:
            order_id: Unique identifier for this order
            amount: Amount to charge in smallest currency unit (e.g., cents)
            currency: ISO 4217 currency code (e.g., "USD", "EUR")
            token: Previously created token (recommended)
            card_number: Card number (if not using token)
            card_expiry_month: Card expiry month (if not using token)
            card_expiry_year: Card expiry year (if not using token)
            card_security_code: Card security code (if not using token)
            description: Optional order description
            authorize_first: If True, authorize only (requires manual capture)

        Returns:
            Dict with payment details or error

        Example:
            mastercard_pay(
                order_id="order-456",
                amount="5000",
                currency="USD",
                token="1234567890123456",
                description="Flight booking payment"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not amount:
            return {"error": "amount is required"}
        if not currency or len(currency) != 3:
            return {"error": "currency must be a 3-letter code (e.g., USD)"}

        if not token and not card_number:
            return {"error": "Either token or card details must be provided"}

        if card_number and (not card_expiry_month or not card_expiry_year):
            return {"error": "Card expiry month and year required when using card number"}

        try:
            return client.pay(
                order_id,
                amount,
                currency,
                token,
                card_number,
                card_expiry_month,
                card_expiry_year,
                card_security_code,
                description,
                authorize_first,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_capture(
        order_id: str,
        transaction_id: str,
        amount: str | None = None,
        currency: str | None = None,
    ) -> dict:
        """
        Capture a previously authorized transaction.

        Use this to capture funds from an authorization created with
        mastercard_authorize. You can capture the full amount or a partial amount.

        Args:
            order_id: Order ID from the original authorization
            transaction_id: Transaction ID to use for the capture
            amount: Amount to capture (omit for full authorized amount)
            currency: Currency code (required if amount is specified)

        Returns:
            Dict with capture details or error

        Example:
            mastercard_capture(
                order_id="order-123",
                transaction_id="2",
                amount="1000",
                currency="USD"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not transaction_id:
            return {"error": "transaction_id is required"}

        if amount and not currency:
            return {"error": "currency is required when amount is specified"}

        try:
            return client.capture(order_id, transaction_id, amount, currency)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_refund(
        order_id: str,
        amount: str,
        currency: str,
        transaction_id: str | None = None,
        target_transaction_id: str | None = None,
    ) -> dict:
        """
        Process a full or partial refund.

        Refunds can be issued against captured transactions. For partial refunds,
        specify the amount to refund.

        Args:
            order_id: Order ID from the original transaction
            amount: Refund amount in smallest currency unit
            currency: ISO 4217 currency code (e.g., "USD")
            transaction_id: Optional transaction ID for the refund
            target_transaction_id: Original transaction to refund (if multiple exist)

        Returns:
            Dict with refund details or error

        Example:
            mastercard_refund(
                order_id="order-456",
                amount="5000",
                currency="USD"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not amount:
            return {"error": "amount is required"}
        if not currency or len(currency) != 3:
            return {"error": "currency must be a 3-letter code (e.g., USD)"}

        try:
            return client.refund(order_id, amount, currency, transaction_id, target_transaction_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_retrieve_transaction(
        order_id: str,
        transaction_id: str | None = None,
    ) -> dict:
        """
        Retrieve transaction status and details.

        If transaction_id is provided, returns details for that specific transaction.
        Otherwise, returns the order summary with all associated transactions.

        Args:
            order_id: Order ID to query
            transaction_id: Optional specific transaction ID

        Returns:
            Dict with transaction/order details or error

        Example:
            mastercard_retrieve_transaction(order_id="order-456")
            mastercard_retrieve_transaction(order_id="order-456", transaction_id="1")
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}

        try:
            return client.retrieve_transaction(order_id, transaction_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_verify_service(
        order_id: str,
        transaction_id: str,
        token: str | None = None,
        card_number: str | None = None,
        card_expiry_month: str | None = None,
        card_expiry_year: str | None = None,
    ) -> dict:
        """
        Verify 3D Secure (3DS) authentication eligibility.

        Check if a card is enrolled in 3D Secure programs like Verified by Visa
        or Mastercard SecureCode.

        Args:
            order_id: Unique identifier for this verification
            transaction_id: Unique transaction ID for the verification
            token: Previously created token (recommended)
            card_number: Card number (if not using token)
            card_expiry_month: Card expiry month (if not using token)
            card_expiry_year: Card expiry year (if not using token)

        Returns:
            Dict with 3DS enrollment status or error

        Example:
            mastercard_verify_service(
                order_id="verify-123",
                transaction_id="1",
                token="1234567890123456"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not transaction_id:
            return {"error": "transaction_id is required"}

        if not token and not card_number:
            return {"error": "Either token or card details must be provided"}

        if card_number and (not card_expiry_month or not card_expiry_year):
            return {"error": "Card expiry month and year required when using card number"}

        try:
            return client.verify_service(
                order_id,
                transaction_id,
                token,
                card_number,
                card_expiry_month,
                card_expiry_year,
            )
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def mastercard_void(
        order_id: str,
        transaction_id: str,
        target_transaction_id: str,
    ) -> dict:
        """
        Void a previously authorized transaction.

        Voids release the hold on funds without capturing. Use this to cancel
        an authorization that won't be captured.

        Args:
            order_id: Order ID from the original authorization
            transaction_id: Unique transaction ID for this void operation
            target_transaction_id: The authorization transaction to void

        Returns:
            Dict with void details or error

        Example:
            mastercard_void(
                order_id="order-123",
                transaction_id="2",
                target_transaction_id="1"
            )
        """
        client = _get_client()
        if isinstance(client, dict):
            return client

        if not order_id:
            return {"error": "order_id is required"}
        if not transaction_id:
            return {"error": "transaction_id is required"}
        if not target_transaction_id:
            return {"error": "target_transaction_id is required"}

        try:
            return client.void(order_id, transaction_id, target_transaction_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
