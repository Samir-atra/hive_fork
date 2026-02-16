"""
Google Meet Tool - Schedule meetings and process minutes.

Supports:
- Creating Google Meet sessions via Calendar API
- Extracting structured outcomes from meeting minutes
- Orchestrating follow-up actions based on outcomes

Requires OAuth 2.0 credentials (matches Calendar tool scope):
- Aden: aden_provider_name="google-calendar"
- Direct: GOOGLE_CALENDAR_ACCESS_TOKEN
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import quote
from zoneinfo import available_timezones

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from framework.credentials.oauth2 import TokenLifecycleManager

    from aden_tools.credentials import CredentialStoreAdapter

logger = logging.getLogger(__name__)

# Google Calendar API base URL (used for Meet creation)
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


def _create_lifecycle_manager(
    credentials: CredentialStoreAdapter,
) -> TokenLifecycleManager | None:
    """
    Create a TokenLifecycleManager for automatic token refresh.

    Currently returns None because token refresh is handled server-side by Aden's
    OAuth infrastructure. When using Aden OAuth, tokens are refreshed automatically
    before they expire. For direct API access (testing), use a short-lived token
    from the OAuth Playground - these tokens expire after ~1 hour.
    """
    return None


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Google Meet tools with the MCP server."""

    # Create lifecycle manager for auto-refresh (if possible)
    lifecycle_manager: TokenLifecycleManager | None = None
    if credentials is not None:
        lifecycle_manager = _create_lifecycle_manager(credentials)
        if lifecycle_manager:
            logger.info("Google Calendar OAuth auto-refresh enabled for Meet tool")

    def _get_token() -> str | None:
        """
        Get OAuth token, refreshing if needed.
        Reuse Google Calendar credentials since Meet is part of Calendar API.
        """
        # Try lifecycle manager first (handles auto-refresh)
        if lifecycle_manager is not None:
            token = lifecycle_manager.sync_get_valid_token()
            if token is not None:
                return token.access_token

        # Fall back to credential store adapter
        if credentials is not None:
            return credentials.get("google_calendar_oauth")

        # Fall back to environment variable
        return os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")

    def _get_headers() -> dict[str, str]:
        """Get authorization headers for API requests."""
        token = _get_token()
        if token is None:
            token = ""  # Will fail auth but prevents "Bearer None" in logs
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _check_credentials() -> dict | None:
        """Check if credentials are configured. Returns error dict if not."""
        token = _get_token()
        if not token:
            return {
                "error": "Google Calendar credentials not configured",
                "help": "Set GOOGLE_CALENDAR_ACCESS_TOKEN environment variable or configure OAuth",
            }
        return None

    def _encode_id(id_value: str) -> str:
        """URL-encode a calendar or event ID for safe use in URLs."""
        return quote(id_value, safe="")

    def _sanitize_error(e: Exception) -> str:
        """Sanitize exception message to avoid leaking sensitive data like tokens."""
        msg = str(e)
        if "Bearer" in msg or "Authorization" in msg:
            return f"{type(e).__name__}: Request failed (details redacted for security)"
        if len(msg) > 200:
            return f"{type(e).__name__}: {msg[:200]}..."
        return msg

    # Pre-compute valid timezones once
    _VALID_TIMEZONES = available_timezones()

    def _validate_timezone(tz: str) -> dict | None:
        """Validate a timezone string. Returns error dict if invalid, None if valid."""
        if tz not in _VALID_TIMEZONES:
            return {"error": f"Invalid timezone '{tz}'. Use IANA format (e.g., 'America/New_York')"}
        return None

    def _handle_response(response: httpx.Response) -> dict:
        """Handle API response and return appropriate result."""
        if response.status_code == 401:
            if lifecycle_manager is not None:
                return {
                    "error": "OAuth token expired and refresh failed",
                    "help": "Re-authenticate via Aden or get a new token",
                }
            return {
                "error": "Invalid or expired OAuth token",
                "help": "Get a new token from https://developers.google.com/oauthplayground/",
            }
        elif response.status_code == 403:
            return {
                "error": "Access denied. Check calendar permissions.",
                "help": "Ensure the OAuth token has calendar.events scope",
            }
        elif response.status_code == 404:
            return {"error": "Resource not found"}
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded. Try again later."}
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": f"API error: {message}"}
            except Exception:
                return {"error": f"API request failed: HTTP {response.status_code}"}
        return response.json()

    @mcp.tool()
    def create_meet_event(
        summary: str,
        start_time: str,
        duration_minutes: int,
        attendees: list[str] | None = None,
        description: str | None = None,
        timezone: str | None = None,
        # Tracking parameters
        workspace_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Create a dedicated Google Meet session (via Calendar API).

        Depending on whether attendees are provided, this creates a calendar event
        with conferenceData (Google Meet link) attached. Even without attendees,
        creates a placeholder event to generate a persistent Meet link.

        Args:
            summary: Meeting title
            start_time: Start time (ISO 8601 format, e.g. "2024-01-15T09:00:00")
            duration_minutes: Duration of the meeting in minutes
            attendees: List of participant email addresses
            description: Meeting agenda or description
            timezone: Timezone for the event (e.g., "America/New_York")
            workspace_id: Tracking parameter
            agent_id: Tracking parameter
            session_id: Tracking parameter

        Returns:
            Dict containing event details and the 'meet_link'
        """
        cred_error = _check_credentials()
        if cred_error:
            return cred_error

        if not summary:
            return {"error": "summary is required"}
        if not start_time:
            return {"error": "start_time is required"}
        if duration_minutes <= 0:
            return {"error": "duration_minutes must be positive"}

        # Calculate end_time
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if start_dt.tzinfo is None and not timezone:
                # Assume UTC if naive and no TZ provided
                start_dt = start_dt.replace(tzinfo=UTC)
            
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            end_time = end_dt.isoformat()
        except ValueError:
            return {"error": "Invalid start_time format. Use ISO 8601."}

        # Request body
        event_body: dict = {
            "summary": summary,
            "description": description or "",
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            # Explicitly request conference data generation
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{uuid.uuid4().hex[:12]}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        if timezone:
            if _validate_timezone(timezone):
                return _validate_timezone(timezone)  # type: ignore[return-value]
            event_body["start"]["timeZone"] = timezone
            event_body["end"]["timeZone"] = timezone

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        # Parameters to enable conference data return
        params = {
            "conferenceDataVersion": 1,
            "sendUpdates": "all" if attendees else "none",
        }

        try:
            response = httpx.post(
                f"{CALENDAR_API_BASE}/calendars/primary/events",
                headers=_get_headers(),
                json=event_body,
                params=params,
                timeout=30.0,
            )
            result = _handle_response(response)
            if "error" in result:
                return result

            # Extract Meet link
            meet_link = result.get("hangoutLink")
            conference_data = result.get("conferenceData", {})
            entry_points = conference_data.get("entryPoints", [])
            
            # Sometimes explicit link is deeper
            if not meet_link:
                for point in entry_points:
                    if point.get("entryPointType") == "video":
                        meet_link = point.get("uri")
                        break
            
            return {
                "event_id": result.get("id"),
                "summary": result.get("summary"),
                "start": result.get("start"),
                "end": result.get("end"),
                "meet_link": meet_link,
                "status": result.get("status"),
                "html_link": result.get("htmlLink"),
            }

        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {_sanitize_error(e)}"}

    @mcp.tool()
    def extract_meeting_outcomes(
        minutes_text: str,
        # Tracking parameters
        workspace_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Extract structured outcomes (Decisions, Action Items) from meeting minutes text.
        
        Uses keyword heuristics to parse common headers like:
        - "Decisions:" or "## Decisions"
        - "Action Items:" or "## Action Items" or "Follow-up:"
        
        Args:
            minutes_text: The plain text of the meeting minutes
            workspace_id: Tracking parameter
            agent_id: Tracking parameter
            session_id: Tracking parameter

        Returns:
            Dict containing lists of 'decisions' and 'action_items'.
        """
        if not minutes_text:
            return {"error": "minutes_text is required"}

        decisions = []
        action_items = []
        
        # Simple line-based parser with state
        lines = minutes_text.split('\n')
        current_section = None
        
        # Regex for headers
        decision_header_re = re.compile(r'^(#+\s*)?decisions?:?', re.IGNORECASE)
        action_header_re = re.compile(r'^(#+\s*)?(action items?|follow[- ]up|tasks):?', re.IGNORECASE)
        
        # Regex for list items
        item_re = re.compile(r'^[\-\*\d\.]+\s+(.*)')

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Check for section headers
            if decision_header_re.match(line_stripped):
                current_section = "decisions"
                continue
            elif action_header_re.match(line_stripped):
                current_section = "actions"
                continue
                
            # Parse items based on current section
            match = item_re.match(line_stripped)
            content = match.group(1) if match else line_stripped
            
            if current_section == "decisions":
                decisions.append(content)
            elif current_section == "actions":
                action_items.append(content)
        
        return {
            "decisions": decisions,
            "action_items": action_items,
            "raw_text_length": len(minutes_text),
            "status": "success" if (decisions or action_items) else "no_structured_data_found"
        }

    @mcp.tool()
    def orchestrate_followup(
        action_items: list[str],
        decisions: list[str],
        owner_email: str | None = None,
        # Tracking parameters
        workspace_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> dict:
        """
        Generate a follow-up plan based on extracted outcomes.
        
        Currently produces a structured plan that an Agent can execute, such as:
        - Sending email summaries (if email tool available)
        - Creating Jira/Task tickets (if task tool available)
        - Scheduling follow-up meetings
        
        Args:
            action_items: List of action items extracted
            decisions: List of decisions made
            owner_email: Optional email of the meeting owner to notify
            workspace_id: Tracking parameter
            agent_id: Tracking parameter
            session_id: Tracking parameter

        Returns:
            Dict representing the recommended follow-up plan
        """
        plan = {
            "summary_email": {
                "recipient": owner_email or "participants",
                "subject": "Meeting Follow-up: Outcomes & Actions",
                "body": f"Decisions:\n{os.linesep.join('- ' + d for d in decisions)}\n\nAction Items:\n{os.linesep.join('- ' + a for a in action_items)}"
            },
            "tasks": [
                {"title": item, "priority": "medium"} for item in action_items
            ],
            "next_steps": "Review this plan and execute necessary tool calls (e.g., gmail_send_email, jira_create_issue)."
        }
        return plan
