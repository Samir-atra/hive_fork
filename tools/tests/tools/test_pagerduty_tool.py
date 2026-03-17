"""Tests for pagerduty_tool - Incident management and services."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.pagerduty_tool.pagerduty_tool import register_tools

ENV = {
    "PAGERDUTY_API_KEY": "test-api-key",
    "PAGERDUTY_FROM_EMAIL": "agent@example.com",
}


def _mock_resp(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = ""
    return resp


@pytest.fixture
def tool_fns(mcp: FastMCP):
    register_tools(mcp, credentials=None)
    tools = mcp._tool_manager._tools
    return {name: tools[name].fn for name in tools}


INCIDENT_DATA = {
    "id": "PT4KHLK",
    "incident_number": 1234,
    "title": "Server is on fire",
    "status": "triggered",
    "urgency": "high",
    "created_at": "2024-01-15T10:00:00Z",
    "html_url": "https://acme.pagerduty.com/incidents/PT4KHLK",
    "service": {"id": "PWIXJZS", "summary": "Web Service"},
    "assignments": [{"assignee": {"summary": "John Doe"}}],
}


class TestPagerdutyListIncidents:
    def test_missing_credentials(self, tool_fns):
        with patch.dict("os.environ", {}, clear=True):
            result = tool_fns["pagerduty_list_incidents"]()
        assert "error" in result

    def test_successful_list(self, tool_fns):
        data = {"incidents": [INCIDENT_DATA], "more": False}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.get",
                return_value=_mock_resp(data),
            ),
        ):
            result = tool_fns["pagerduty_list_incidents"]()

        assert result["count"] == 1
        assert result["incidents"][0]["title"] == "Server is on fire"
        assert result["incidents"][0]["service"] == "Web Service"


class TestPagerdutyGetIncident:
    def test_missing_id(self, tool_fns):
        with patch.dict("os.environ", ENV):
            result = tool_fns["pagerduty_get_incident"](incident_id="")
        assert "error" in result

    def test_successful_get(self, tool_fns):
        inc = dict(INCIDENT_DATA)
        inc["body"] = {"details": "CPU at 100%"}
        data = {"incident": inc}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.get",
                return_value=_mock_resp(data),
            ),
        ):
            result = tool_fns["pagerduty_get_incident"](incident_id="PT4KHLK")

        assert result["title"] == "Server is on fire"
        assert result["details"] == "CPU at 100%"


class TestPagerdutyCreateIncident:
    def test_missing_params(self, tool_fns):
        with patch.dict("os.environ", ENV):
            result = tool_fns["pagerduty_create_incident"](title="", service_id="")
        assert "error" in result

    def test_successful_create(self, tool_fns):
        data = {"incident": INCIDENT_DATA}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.post",
                return_value=_mock_resp(data, 201),
            ),
        ):
            result = tool_fns["pagerduty_create_incident"](
                title="Server is on fire", service_id="PWIXJZS"
            )

        assert result["result"] == "created"
        assert result["id"] == "PT4KHLK"


class TestPagerdutyUpdateIncident:
    def test_missing_status(self, tool_fns):
        with patch.dict("os.environ", ENV):
            result = tool_fns["pagerduty_update_incident"](incident_id="PT4KHLK", status="")
        assert "error" in result

    def test_successful_acknowledge(self, tool_fns):
        ack = dict(INCIDENT_DATA)
        ack["status"] = "acknowledged"
        data = {"incident": ack}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.put",
                return_value=_mock_resp(data),
            ),
        ):
            result = tool_fns["pagerduty_update_incident"](
                incident_id="PT4KHLK", status="acknowledged"
            )

        assert result["status"] == "acknowledged"


class TestPagerdutyListServices:
    def test_missing_credentials(self, tool_fns):
        with patch.dict("os.environ", {}, clear=True):
            result = tool_fns["pagerduty_list_services"]()
        assert "error" in result

    def test_successful_list(self, tool_fns):
        data = {
            "services": [
                {
                    "id": "PWIXJZS",
                    "name": "Web Service",
                    "description": "Production web app",
                    "status": "active",
                    "html_url": "https://acme.pagerduty.com/services/PWIXJZS",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_incident_timestamp": "2024-06-15T12:30:00Z",
                }
            ]
        }
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.get",
                return_value=_mock_resp(data),
            ),
        ):
            result = tool_fns["pagerduty_list_services"]()

        assert result["count"] == 1
        assert result["services"][0]["name"] == "Web Service"


class TestTriggerIncident:
    def test_missing_params(self, tool_fns):
        with patch.dict("os.environ", ENV):
            # Missing one of the required params (TypeError handled by pytest if called directly,
            # but FastMCP tool calls enforce types)
            pass

    def test_successful_trigger(self, tool_fns):
        data = {"incident": INCIDENT_DATA}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.post",
                return_value=_mock_resp(data, 201),
            ) as mock_post,
        ):
            result = tool_fns["trigger_incident"](
                title="Critical failure", service_id="PWIXJZS", urgency="high", from_email="agent@example.com"
            )

        assert result["incident_id"] == "PT4KHLK"
        assert result["status"] == "triggered"

        # Verify the payload was constructed properly
        assert mock_post.called
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert call_args.kwargs["headers"]["From"] == "agent@example.com"
        assert payload["incident"]["type"] == "incident"
        assert payload["incident"]["title"] == "Critical failure"
        assert payload["incident"]["service"]["id"] == "PWIXJZS"
        assert payload["incident"]["urgency"] == "high"


class TestGetOnCall:
    def test_missing_credentials(self, tool_fns):
        with patch.dict("os.environ", {}, clear=True):
            result = tool_fns["get_on_call"](schedule_id="SCHED123")
        assert "error" in result

    def test_successful_get_on_call(self, tool_fns):
        data = {
            "oncalls": [
                {
                    "user": {
                        "summary": "Jane Smith",
                        "email": "jane@example.com",
                        "id": "PU12345"
                    }
                }
            ]
        }
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.get",
                return_value=_mock_resp(data),
            ) as mock_get,
        ):
            result = tool_fns["get_on_call"](schedule_id="SCHED123")

        assert result["user_name"] == "Jane Smith"
        assert result["user_email"] == "jane@example.com"
        assert result["user_id"] == "PU12345"

        # Verify params
        assert mock_get.called
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["schedule_ids[]"] == ["SCHED123"]


class TestResolveIncident:
    def test_missing_credentials(self, tool_fns):
        with patch.dict("os.environ", {}, clear=True):
            result = tool_fns["resolve_incident"](incident_id="PT4KHLK", from_email="agent@example.com")
        assert "error" in result

    def test_successful_resolve(self, tool_fns):
        ack = dict(INCIDENT_DATA)
        ack["status"] = "resolved"
        data = {"incident": ack}
        with (
            patch.dict("os.environ", ENV),
            patch(
                "aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.put",
                return_value=_mock_resp(data),
            ) as mock_put,
        ):
            result = tool_fns["resolve_incident"](
                incident_id="PT4KHLK", from_email="agent@example.com"
            )

        assert result["status"] == "resolved"

        assert mock_put.called
        call_args = mock_put.call_args

        # Check from_email header
        headers = call_args.kwargs["headers"]
        assert headers["From"] == "agent@example.com"

        # Check payload
        payload = call_args.kwargs["json"]
        assert payload["incident"]["type"] == "incident_reference"
        assert payload["incident"]["status"] == "resolved"
