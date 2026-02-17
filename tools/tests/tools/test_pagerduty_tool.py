"""
Tests for PagerDuty tool.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.pagerduty_tool.pagerduty_tool import (
    _PagerDutyClient,
    register_tools,
)


class TestPagerDutyClient:
    def setup_method(self):
        self.client = _PagerDutyClient("pd_test_token", "user@example.com")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Authorization"] == "Token token=pd_test_token"
        assert headers["Accept"] == "application/vnd.pagerduty+json;version=2"
        assert headers["Content-Type"] == "application/json"
        assert headers["From"] == "user@example.com"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_request_success(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"foo": "bar"}
        mock_request.return_value = mock_response

        result = self.client._request("GET", "/test")

        assert result["success"] is True
        assert result["data"]["foo"] == "bar"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_request_http_error(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.side_effect = Exception("Not JSON")
        
        mock_request.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )

        result = self.client._request("GET", "/test")

        assert "error" in result
        assert "HTTP 404" in result["error"]
        assert "Not Found" in result["error"]


class TestPagerDutyTools:
    @pytest.fixture
    def mcp(self):
        return FastMCP("test-server")

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_trigger_incident(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "incident": {
                "id": "P12345",
                "title": "Serious Issue"
            }
        }
        mock_request.return_value = mock_response

        with patch("os.getenv", side_effect=lambda k: "pd_test" if k == "PAGERDUTY_API_KEY" else None):
            register_tools(mcp, credentials=None)
            trigger_incident = mcp._tool_manager._tools["pagerduty_trigger_incident"].fn

            result = trigger_incident(
                title="Serious Issue",
                service_id="SVC123",
                urgency="high",
                details="Something is broken"
            )

            assert result["success"] is True
            assert result["data"]["incident"]["id"] == "P12345"
            
            # Verify request
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "https://api.pagerduty.com/incidents"
            assert kwargs["json"]["incident"]["title"] == "Serious Issue"
            assert kwargs["json"]["incident"]["service"]["id"] == "SVC123"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_acknowledge_incident(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"incident": {"id": "P123", "status": "acknowledged"}}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            acknowledge = mcp._tool_manager._tools["pagerduty_acknowledge_incident"].fn

            result = acknowledge(incident_id="P123")

            assert result["success"] is True
            assert result["data"]["incident"]["status"] == "acknowledged"
            assert mock_request.call_args[0][0] == "PUT"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_resolve_incident(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"incident": {"id": "P123", "status": "resolved"}}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            resolve = mcp._tool_manager._tools["pagerduty_resolve_incident"].fn

            result = resolve(incident_id="P123")

            assert result["success"] is True
            assert result["data"]["incident"]["status"] == "resolved"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_get_incident(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"incident": {"id": "P123", "title": "Test"}}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            get_incident = mcp._tool_manager._tools["pagerduty_get_incident"].fn

            result = get_incident(incident_id="P123")

            assert result["success"] is True
            assert result["data"]["incident"]["id"] == "P123"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_list_incidents(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"incidents": [{"id": "P1"}]}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            list_incidents = mcp._tool_manager._tools["pagerduty_list_incidents"].fn

            result = list_incidents(statuses=["triggered"])

            assert result["success"] is True
            assert len(result["data"]["incidents"]) == 1
            _, kwargs = mock_request.call_args
            assert kwargs["params"]["statuses[]"] == ["triggered"]

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_add_incident_note(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"note": {"id": "N1", "content": "Hello"}}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            add_note = mcp._tool_manager._tools["pagerduty_add_incident_note"].fn

            result = add_note(incident_id="P123", content="Hello")

            assert result["success"] is True
            assert result["data"]["note"]["content"] == "Hello"
            _, kwargs = mock_request.call_args
            assert kwargs["json"]["note"]["content"] == "Hello"

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_list_services(self, mock_request, mcp):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"services": [{"id": "S1", "name": "Web"}]}
        mock_request.return_value = mock_response

        with patch("os.getenv", return_value="pd_test"):
            register_tools(mcp, credentials=None)
            list_services = mcp._tool_manager._tools["pagerduty_list_services"].fn

            result = list_services(query="Web")

            assert result["success"] is True
            assert len(result["data"]["services"]) == 1
            
            # Verify request
            _, kwargs = mock_request.call_args
            assert kwargs["params"]["query"] == "Web"
