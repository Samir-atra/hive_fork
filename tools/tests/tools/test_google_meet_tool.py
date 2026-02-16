"""Tests for Google Meet tool (FastMCP)."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.google_meet_tool import register_tools


@pytest.fixture
def meet_tools(mcp: FastMCP):
    """Register and return Google Meet tool functions."""
    register_tools(mcp)
    tools: Any = mcp._tool_manager._tools  # type: ignore
    return {
        "create_meet_event": tools["create_meet_event"].fn,
        "extract_meeting_outcomes": tools["extract_meeting_outcomes"].fn,
        "orchestrate_followup": tools["orchestrate_followup"].fn,
    }


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    return mock


class TestCreateMeetEvent:
    """Tests for create_meet_event."""

    @patch("aden_tools.tools.google_meet_tool.google_meet_tool.httpx.post")
    def test_create_meet_success(self, mock_post, meet_tools, monkeypatch):
        """create_meet_event returns event with meet link."""
        monkeypatch.setenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "test-token")

        mock_post.return_value = _mock_response(
            200,
            {
                "id": "event123",
                "summary": "Team Sync",
                "start": {"dateTime": "2024-01-15T09:00:00Z"},
                "end": {"dateTime": "2024-01-15T10:00:00Z"},
                "hangoutLink": "https://meet.google.com/abc-defg-hij",
                "status": "confirmed",
            },
        )

        result = meet_tools["create_meet_event"](
            summary="Team Sync",
            start_time="2024-01-15T09:00:00Z",
            duration_minutes=60,
        )

        assert result["meet_link"] == "https://meet.google.com/abc-defg-hij"
        assert result["event_id"] == "event123"
        
        # Verify conferenceData was requested
        call_kwargs = mock_post.call_args
        body = call_kwargs[1]["json"]
        assert "conferenceData" in body
        assert body["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"] == "hangoutsMeet"

    def test_create_meet_no_credentials(self, meet_tools, monkeypatch):
        """create_meet_event without credentials returns error."""
        monkeypatch.delenv("GOOGLE_CALENDAR_ACCESS_TOKEN", raising=False)

        result = meet_tools["create_meet_event"](
            summary="Test",
            start_time="2024-01-15T09:00:00Z",
            duration_minutes=30,
        )

        assert "error" in result
        assert "Calendar credentials not configured" in result["error"]

    @patch("aden_tools.tools.google_meet_tool.google_meet_tool.httpx.post")
    def test_create_meet_with_attendees(self, mock_post, meet_tools, monkeypatch):
        """create_meet_event adds attendees."""
        monkeypatch.setenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "test-token")
        
        mock_post.return_value = _mock_response(200, {"id": "123", "hangoutLink": "link"})

        meet_tools["create_meet_event"](
            summary="Test",
            start_time="2024-01-15T09:00:00Z",
            duration_minutes=30,
            attendees=["test@example.com"],
        )

        body = mock_post.call_args[1]["json"]
        assert body["attendees"] == [{"email": "test@example.com"}]


class TestExtractMeetingOutcomes:
    """Tests for extract_meeting_outcomes."""

    def test_extract_structured_outcomes(self, meet_tools):
        """extract_meeting_outcomes parses decisions and actions."""
        minutes = """
        Meeting Minutes - 2024-01-15
        
        ## Decisions
        - We will use Python for the backend.
        - MVP launch date is set for March 1st.
        
        ## Action Items
        - John: Setup repository
        - Jane: Create tickets
        """
        
        result = meet_tools["extract_meeting_outcomes"](minutes_text=minutes)
        
        assert "decisions" in result
        assert len(result["decisions"]) == 2
        assert "Python" in result["decisions"][0]
        
        assert "action_items" in result
        assert len(result["action_items"]) == 2
        assert "John" in result["action_items"][0]

    def test_extract_unstructured(self, meet_tools):
        """extract_meeting_outcomes returns empty lists if no sections found."""
        minutes = "Just some random notes without headers."
        
        result = meet_tools["extract_meeting_outcomes"](minutes_text=minutes)
        
        assert result["decisions"] == []
        assert result["action_items"] == []
        assert result["status"] == "no_structured_data_found"


class TestOrchestrateFollowup:
    """Tests for orchestrate_followup."""

    def test_orchestrate_plan_generation(self, meet_tools):
        """orchestrate_followup returns structured plan."""
        result = meet_tools["orchestrate_followup"](
            action_items=["Task 1", "Task 2"],
            decisions=["Decision A"],
            owner_email="boss@example.com",
        )
        
        assert "summary_email" in result
        assert result["summary_email"]["recipient"] == "boss@example.com"
        assert "tasks" in result
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["title"] == "Task 1"
