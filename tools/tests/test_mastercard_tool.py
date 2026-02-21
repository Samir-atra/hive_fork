"""Tests for Mastercard payment tool."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.mastercard_tool.mastercard_tool import (
    _MastercardClient,
    register_tools,
)


class TestMastercardClient:
    """Tests for the _MastercardClient class."""

    def test_init(self):
        """Client initializes with correct credentials."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        assert client._merchant_id == "TESTMERCHANT"
        assert client._api_password == "test_password"
        assert client._base_url == "https://test-gateway.mastercard.com"

    def test_auth_tuple(self):
        """Auth tuple is correctly formatted."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        auth = client._auth
        assert auth == ("merchant.TESTMERCHANT", "test_password")

    def test_api_url(self):
        """API URL is correctly constructed."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        url = client._api_url("/token")
        assert "TESTMERCHANT" in url
        assert "/token" in url

    def _mock_response(self, status_code, json_data=None):
        """Create a mock HTTP response."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        if json_data:
            response.json.return_value = json_data
        return response

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_create_token_success(self, mock_put):
        """Create token returns token on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "repositoryId": "1234567890123456",
                "result": "SUCCESS",
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.create_token(
            card_number="5123456789012346",
            card_expiry_month="05",
            card_expiry_year="2027",
        )

        assert result["token"] == "1234567890123456"
        assert result["status"] == "SUCCESS"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_authorize_success(self, mock_put):
        """Authorize returns authorization details on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "transaction": {"id": "1", "authorizationCode": "123456"},
                "order": {"totalAuthorizedAmount": "1000", "currency": "USD"},
                "result": "SUCCESS",
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.authorize(
            order_id="order-123",
            amount="1000",
            currency="USD",
            token="1234567890123456",
        )

        assert result["order_id"] == "order-123"
        assert result["status"] == "SUCCESS"
        assert result["amount"] == "1000"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_pay_success(self, mock_put):
        """Pay returns payment details on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "transaction": {"id": "1", "authorizationCode": "123456"},
                "order": {
                    "totalAuthorizedAmount": "5000",
                    "totalCapturedAmount": "5000",
                    "currency": "USD",
                },
                "result": "SUCCESS",
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.pay(
            order_id="order-456",
            amount="5000",
            currency="USD",
            token="1234567890123456",
        )

        assert result["order_id"] == "order-456"
        assert result["status"] == "SUCCESS"
        assert result["captured_amount"] == "5000"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_capture_success(self, mock_put):
        """Capture returns capture details on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "transaction": {"id": "2"},
                "order": {"totalCapturedAmount": "1000", "currency": "USD"},
                "result": "SUCCESS",
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.capture(
            order_id="order-123",
            transaction_id="2",
            amount="1000",
            currency="USD",
        )

        assert result["order_id"] == "order-123"
        assert result["status"] == "SUCCESS"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_refund_success(self, mock_put):
        """Refund returns refund details on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "transaction": {"id": "3", "amount": "5000"},
                "order": {"currency": "USD"},
                "result": "SUCCESS",
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.refund(
            order_id="order-456",
            amount="5000",
            currency="USD",
        )

        assert result["order_id"] == "order-456"
        assert result["status"] == "SUCCESS"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.get")
    def test_retrieve_transaction_order_success(self, mock_get):
        """Retrieve transaction returns order details on success."""
        mock_get.return_value = self._mock_response(
            200,
            {
                "order": {
                    "totalAuthorizedAmount": "5000",
                    "totalCapturedAmount": "5000",
                    "totalRefundedAmount": "0",
                    "currency": "USD",
                    "status": "CAPTURED",
                },
                "transaction": [
                    {
                        "id": "1",
                        "type": "PURCHASE",
                        "amount": "5000",
                        "currency": "USD",
                        "status": "CAPTURED",
                    }
                ],
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.retrieve_transaction(order_id="order-456")

        assert result["order_id"] == "order-456"
        assert result["status"] == "CAPTURED"
        assert len(result["transactions"]) == 1

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.get")
    def test_retrieve_transaction_specific_success(self, mock_get):
        """Retrieve specific transaction returns transaction details."""
        mock_get.return_value = self._mock_response(
            200,
            {
                "transaction": {
                    "id": "1",
                    "type": "PURCHASE",
                    "amount": "5000",
                    "currency": "USD",
                    "status": "CAPTURED",
                    "authorizationCode": "123456",
                },
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.retrieve_transaction(order_id="order-456", transaction_id="1")

        assert result["order_id"] == "order-456"
        assert result["transaction_id"] == "1"
        assert result["status"] == "CAPTURED"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_verify_service_success(self, mock_put):
        """Verify service returns 3DS enrollment status."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "3DS": {
                    "secureId": "secure-123",
                    "enrolled": "Y",
                    "acsUrl": "https://acs.example.com",
                    "payerAuthenticationRequest": "paReq123",
                },
                "result": "SUCCESS",
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.verify_service(
            order_id="verify-123",
            transaction_id="1",
            token="1234567890123456",
        )

        assert result["order_id"] == "verify-123"
        assert result["enrolled"] == "Y"
        assert result["secure_id"] == "secure-123"

    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_void_success(self, mock_put):
        """Void returns void details on success."""
        mock_put.return_value = self._mock_response(
            200,
            {
                "transaction": {"id": "2"},
                "result": "SUCCESS",
                "response": {"gatewayCode": "APPROVED"},
                "correlationId": "corr-123",
            },
        )

        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        result = client.void(
            order_id="order-123",
            transaction_id="2",
            target_transaction_id="1",
        )

        assert result["order_id"] == "order-123"
        assert result["voided_transaction_id"] == "1"
        assert result["status"] == "SUCCESS"

    def test_handle_response_401(self):
        """Handle response returns error for 401."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        response = self._mock_response(401)
        result = client._handle_response(response)
        assert "error" in result
        assert "Invalid" in result["error"]

    def test_handle_response_404(self):
        """Handle response returns error for 404."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        response = self._mock_response(404)
        result = client._handle_response(response)
        assert "error" in result
        assert "not found" in result["error"]

    def test_handle_response_429(self):
        """Handle response returns error for rate limit."""
        client = _MastercardClient(
            merchant_id="TESTMERCHANT",
            api_password="test_password",
            base_url="https://test-gateway.mastercard.com",
        )
        response = self._mock_response(429)
        result = client._handle_response(response)
        assert "error" in result
        assert "rate limit" in result["error"]


class TestMastercardToolRegistration:
    """Tests for tool registration."""

    def test_register_tools(self):
        """Tools are registered correctly."""
        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = list(mcp._tool_manager._tools.keys())

        assert "mastercard_create_token" in tools
        assert "mastercard_authorize" in tools
        assert "mastercard_pay" in tools
        assert "mastercard_capture" in tools
        assert "mastercard_refund" in tools
        assert "mastercard_retrieve_transaction" in tools
        assert "mastercard_verify_service" in tools
        assert "mastercard_void" in tools


class TestMastercardToolValidation:
    """Tests for input validation in tools."""

    @patch.dict("os.environ", {}, clear=True)
    def test_no_credentials_error(self):
        """Tools return error when credentials are not configured."""
        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools

        create_token = tools["mastercard_create_token"].fn
        result = create_token(
            card_number="5123456789012346",
            card_expiry_month="05",
            card_expiry_year="2027",
        )

        assert "error" in result
        assert "not configured" in result["error"]

    @patch.dict(
        "os.environ",
        {
            "MASTERCARD_MERCHANT_ID": "TESTMERCHANT",
            "MASTERCARD_API_PASSWORD": "test_password",
        },
    )
    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_create_token_validation(self, mock_put):
        """Create token validates input."""
        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools
        create_token = tools["mastercard_create_token"].fn

        result = create_token(
            card_number="123",
            card_expiry_month="05",
            card_expiry_year="2027",
        )
        assert "error" in result
        assert "Invalid card number" in result["error"]

        result = create_token(
            card_number="5123456789012346",
            card_expiry_month="5",
            card_expiry_year="2027",
        )
        assert "error" in result
        assert "month must be 2 digits" in result["error"]

        result = create_token(
            card_number="5123456789012346",
            card_expiry_month="05",
            card_expiry_year="27",
        )
        assert "error" in result
        assert "year must be 4 digits" in result["error"]

    @patch.dict(
        "os.environ",
        {
            "MASTERCARD_MERCHANT_ID": "TESTMERCHANT",
            "MASTERCARD_API_PASSWORD": "test_password",
        },
    )
    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_authorize_validation(self, mock_put):
        """Authorize validates input."""
        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools
        authorize = tools["mastercard_authorize"].fn

        result = authorize(
            order_id="",
            amount="1000",
            currency="USD",
            token="1234567890123456",
        )
        assert "error" in result
        assert "order_id is required" in result["error"]

        result = authorize(
            order_id="order-123",
            amount="",
            currency="USD",
            token="1234567890123456",
        )
        assert "error" in result
        assert "amount is required" in result["error"]

        result = authorize(
            order_id="order-123",
            amount="1000",
            currency="US",
            token="1234567890123456",
        )
        assert "error" in result
        assert "3-letter code" in result["error"]

        result = authorize(
            order_id="order-123",
            amount="1000",
            currency="USD",
        )
        assert "error" in result
        assert "Either token or card details" in result["error"]

    @patch.dict(
        "os.environ",
        {
            "MASTERCARD_MERCHANT_ID": "TESTMERCHANT",
            "MASTERCARD_API_PASSWORD": "test_password",
        },
    )
    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_refund_validation(self, mock_put):
        """Refund validates input."""
        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools
        refund = tools["mastercard_refund"].fn

        result = refund(
            order_id="order-123",
            amount="",
            currency="USD",
        )
        assert "error" in result
        assert "amount is required" in result["error"]

        result = refund(
            order_id="order-123",
            amount="1000",
            currency="US",
        )
        assert "error" in result
        assert "3-letter code" in result["error"]

    @patch.dict(
        "os.environ",
        {
            "MASTERCARD_MERCHANT_ID": "TESTMERCHANT",
            "MASTERCARD_API_PASSWORD": "test_password",
        },
    )
    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_timeout_handling(self, mock_put):
        """Tools handle timeouts gracefully."""
        mock_put.side_effect = httpx.TimeoutException("timed out")

        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools
        create_token = tools["mastercard_create_token"].fn

        result = create_token(
            card_number="5123456789012346",
            card_expiry_month="05",
            card_expiry_year="2027",
        )

        assert "error" in result
        assert "timed out" in result["error"]

    @patch.dict(
        "os.environ",
        {
            "MASTERCARD_MERCHANT_ID": "TESTMERCHANT",
            "MASTERCARD_API_PASSWORD": "test_password",
        },
    )
    @patch("aden_tools.tools.mastercard_tool.mastercard_tool.httpx.put")
    def test_network_error_handling(self, mock_put):
        """Tools handle network errors gracefully."""
        mock_put.side_effect = httpx.RequestError("connection failed")

        from fastmcp import FastMCP

        mcp = FastMCP("test-mastercard")
        register_tools(mcp)

        tools = mcp._tool_manager._tools
        create_token = tools["mastercard_create_token"].fn

        result = create_token(
            card_number="5123456789012346",
            card_expiry_month="05",
            card_expiry_year="2027",
        )

        assert "error" in result
        assert "Network error" in result["error"]
