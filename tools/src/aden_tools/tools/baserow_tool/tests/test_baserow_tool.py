"""Tests for Baserow tool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.baserow_tool.baserow_tool import (
    DEFAULT_BASEROW_URL,
    _BaserowClient,
    register_tools,
)


class TestBaserowClient:
    def setup_method(self):
        self.client = _BaserowClient("test-token")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Token test-token"
        assert headers["Content-Type"] == "application/json"

    def test_custom_url(self):
        client = _BaserowClient("tok", "https://baserow.example.com/")
        assert client._base_url == "https://baserow.example.com"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": 1, "Name": "Test"}
        assert self.client._handle_response(response) == {"id": 1, "Name": "Test"}

    def test_handle_response_204(self):
        response = MagicMock()
        response.status_code = 204
        assert self.client._handle_response(response) == {"success": True}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid or expired"),
            (403, "Insufficient permissions"),
            (404, "not found"),
            (429, "rate limit"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring in result["error"]

    @patch("aden_tools.tools.baserow_tool.baserow_tool.httpx.get")
    def test_list_rows(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        result = self.client.list_rows(123, search="findme")

        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == f"{DEFAULT_BASEROW_URL}/api/database/rows/table/123/"
        assert kwargs["params"]["search"] == "findme"
        assert kwargs["params"]["user_field_names"] == "true"
        assert result == {"results": []}

    @patch("aden_tools.tools.baserow_tool.baserow_tool.httpx.post")
    def test_create_row(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response

        data = {"Name": "New"}
        result = self.client.create_row(123, data)

        mock_post.assert_called_once_with(
            f"{DEFAULT_BASEROW_URL}/api/database/rows/table/123/",
            headers=self.client._headers,
            params={"user_field_names": "true"},
            json=data,
            timeout=30.0,
        )
        assert result["id"] == 1


class TestToolRegistration:
    def test_register_tools_registers_all(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 5

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)

        list_fn = next(fn for fn in registered_fns if fn.__name__ == "baserow_list_rows")
        result = list_fn(table_id=1)
        assert "error" in result
        assert "token not configured" in result["error"]

    @patch("aden_tools.tools.baserow_tool.baserow_tool.httpx.get")
    def test_credentials_from_store(self, mock_get):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_store = MagicMock()
        cred_store.get.side_effect = lambda key: "test-token" if key == "baserow" else None
        
        register_tools(mcp, credentials=cred_store)
        list_fn = next(fn for fn in registered_fns if fn.__name__ == "baserow_list_rows")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        list_fn(table_id=123)

        call_headers = mock_get.call_args.kwargs["headers"]
        assert call_headers["Authorization"] == "Token test-token"


class TestCredentialSpec:
    def test_baserow_spec_exists(self):
        from aden_tools.credentials import CREDENTIAL_SPECS
        assert "baserow" in CREDENTIAL_SPECS
        assert CREDENTIAL_SPECS["baserow"].env_var == "BASEROW_TOKEN"
