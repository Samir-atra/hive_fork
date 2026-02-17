"""
Integration tests for PagerDuty tool.
Verifies the integration between CredentialStoreAdapter, FastMCP, and PagerDutyTool.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.credentials import CredentialStoreAdapter
from aden_tools.tools.pagerduty_tool import register_tools


class TestPagerDutyIntegration:
    @pytest.fixture
    def credentials(self):
        """Mock credentials adapter."""
        return CredentialStoreAdapter.for_testing({
            "pagerduty": "test-api-key",
            "pagerduty_email": "bot@aden.ai"
        })

    @pytest.fixture
    def mcp(self):
        """FastMCP instance for testing."""
        return FastMCP("pagerduty-integration-test")

    @patch("aden_tools.tools.pagerduty_tool.pagerduty_tool.httpx.request")
    def test_full_incident_flow(self, mock_request, mcp, credentials):
        """Test a complete flow: registration -> tool lookup -> execution."""
        
        # 1. Register tools
        register_tools(mcp, credentials=credentials)
        
        # Verify tools are registered in MCP
        assert "pagerduty_trigger_incident" in mcp._tool_manager._tools
        assert "pagerduty_acknowledge_incident" in mcp._tool_manager._tools
        
        # 2. Setup mock for incident trigger
        trigger_response = MagicMock()
        trigger_response.status_code = 201
        trigger_response.json.return_value = {
            "incident": {
                "id": "INC-001",
                "title": "Outage",
                "status": "triggered"
            }
        }
        
        # 3. Setup mock for incident acknowledge
        ack_response = MagicMock()
        ack_response.status_code = 200
        ack_response.json.return_value = {
            "incident": {
                "id": "INC-001",
                "status": "acknowledged"
            }
        }
        
        mock_request.side_effect = [trigger_response, ack_response]

        # 4. Trigger incident via MCP tool reference
        trigger_tool = mcp._tool_manager._tools["pagerduty_trigger_incident"].fn
        result_trigger = trigger_tool(title="Outage", service_id="SVC-1")
        
        assert result_trigger["success"] is True
        assert result_trigger["data"]["incident"]["id"] == "INC-001"
        
        # Verify the 'From' header was passed from credentials
        _, kwargs = mock_request.call_args_list[0]
        assert kwargs["headers"]["From"] == "bot@aden.ai"
        assert kwargs["headers"]["Authorization"] == "Token token=test-api-key"

        # 5. Acknowledge incident
        ack_tool = mcp._tool_manager._tools["pagerduty_acknowledge_incident"].fn
        result_ack = ack_tool(incident_id="INC-001")
        
        assert result_ack["success"] is True
        assert result_ack["data"]["incident"]["status"] == "acknowledged"
        
        # Verify PUT request
        args, kwargs = mock_request.call_args_list[1]
        assert args[0] == "PUT"
        assert args[1].endswith("/incidents/INC-001")
        assert kwargs["json"]["incident"]["status"] == "acknowledged"

    def test_missing_credentials(self, mcp):
        """Test behavior when credentials are missing."""
        # Use an empty store
        empty_creds = CredentialStoreAdapter.for_testing({})
        register_tools(mcp, credentials=empty_creds)
        
        trigger_tool = mcp._tool_manager._tools["pagerduty_trigger_incident"].fn
        
        with patch("os.getenv", return_value=None):
            result = trigger_tool(title="Fail", service_id="S1")
            
            assert "error" in result
            assert "PagerDuty credentials not configured" in result["error"]
