"""
Audit Logger for Governance Events

Provides comprehensive audit trail logging for all governance-related events
including permission checks, risk assessments, approvals, and blocks.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from framework.governance.config import AuditConfig

logger = logging.getLogger(__name__)


class AuditEventType(StrEnum):
    """Types of audit events."""

    PERMISSION_CHECK = "permission_check"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    RISK_ASSESSMENT = "risk_assessment"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    TOOL_BLOCKED = "tool_blocked"
    TOOL_EXECUTED = "tool_executed"
    DATA_ACCESS = "data_access"
    DATA_ISOLATION_VIOLATION = "data_isolation_violation"
    POLICY_VIOLATION = "policy_violation"
    ESCALATION = "escalation"
    CONFIG_CHANGE = "config_change"


@dataclass
class AuditEvent:
    """An audit event record."""

    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.now)
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    decision: str | None = None
    reason: str | None = None
    risk_level: str | None = None
    actor: str | None = None
    session_id: str | None = None
    agent_id: str | None = None
    execution_id: str | None = None
    node_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "decision": self.decision,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "actor": self.actor,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "node_id": self.node_id,
            "context": self.context,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

        if include_sensitive and self.tool_input:
            result["tool_input"] = self.tool_input

        return result

    def to_json(self, include_sensitive: bool = False) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(include_sensitive))


class AuditLogger:
    """
    Comprehensive audit logger for governance events.

    Features:
    - File-based audit log storage
    - Event Bus integration for real-time streaming
    - Sensitive data redaction
    - Configurable event filtering
    - Statistics and querying
    """

    def __init__(
        self,
        config: AuditConfig,
        event_bus: Any | None = None,
    ):
        self.config = config
        self._event_bus = event_bus
        self._events: list[AuditEvent] = []
        self._max_events = 10000
        self._compiled_redact_patterns: list[re.Pattern] | None = None

        if config.log_to_file and config.log_file_path:
            self._ensure_log_file(config.log_file_path)

    def _ensure_log_file(self, path: str) -> None:
        """Ensure log file directory exists."""
        log_path = Path(path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_redact_patterns(self) -> list[re.Pattern]:
        """Get compiled redaction patterns."""
        if self._compiled_redact_patterns is None:
            self._compiled_redact_patterns = [
                re.compile(pattern, re.IGNORECASE) for pattern in self.config.redact_patterns
            ]
        return self._compiled_redact_patterns

    def _redact_sensitive(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive values from data."""
        if self.config.include_sensitive_params:
            return data

        patterns = self._get_redact_patterns()
        redacted = {}

        for key, value in data.items():
            key_lower = key.lower()
            is_sensitive = any(p.search(key_lower) for p in patterns)

            if is_sensitive:
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive(v) if isinstance(v, dict) else v for v in value
                ]
            else:
                redacted[key] = value

        return redacted

    async def log_event(self, event: AuditEvent) -> None:
        """Log an audit event."""
        if not self.config.enabled:
            return

        should_log = self._should_log_event(event.event_type)
        if not should_log:
            return

        if event.tool_input:
            event.tool_input = self._redact_sensitive(event.tool_input)

        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

        if self.config.log_to_file and self.config.log_file_path:
            await self._write_to_file(event)

        if self.config.log_to_event_bus and self._event_bus:
            await self._publish_to_event_bus(event)

        logger.debug(f"Audit event logged: {event.event_type.value}")

    def _should_log_event(self, event_type: AuditEventType) -> bool:
        """Check if event type should be logged."""
        event_logging_map = {
            AuditEventType.PERMISSION_CHECK: self.config.log_permission_checks,
            AuditEventType.PERMISSION_GRANTED: self.config.log_permission_checks,
            AuditEventType.PERMISSION_DENIED: self.config.log_permission_checks,
            AuditEventType.RISK_ASSESSMENT: self.config.log_risk_assessments,
            AuditEventType.APPROVAL_REQUESTED: self.config.log_approvals,
            AuditEventType.APPROVAL_GRANTED: self.config.log_approvals,
            AuditEventType.APPROVAL_DENIED: self.config.log_approvals,
            AuditEventType.TOOL_BLOCKED: self.config.log_blocks,
            AuditEventType.TOOL_EXECUTED: self.config.log_tool_calls,
            AuditEventType.DATA_ACCESS: self.config.log_data_access,
            AuditEventType.DATA_ISOLATION_VIOLATION: self.config.log_data_access,
            AuditEventType.POLICY_VIOLATION: self.config.log_blocks,
            AuditEventType.ESCALATION: True,
            AuditEventType.CONFIG_CHANGE: True,
        }
        return event_logging_map.get(event_type, True)

    async def _write_to_file(self, event: AuditEvent) -> None:
        """Write event to log file."""
        try:
            log_path = Path(self.config.log_file_path)
            with open(log_path, "a") as f:
                f.write(event.to_json(include_sensitive=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")

    async def _publish_to_event_bus(self, event: AuditEvent) -> None:
        """Publish event to event bus."""
        try:
            if self._event_bus:
                from framework.runtime.event_bus import AgentEvent, EventType

                agent_event = AgentEvent(
                    type=EventType.CUSTOM,
                    stream_id=event.session_id or "governance",
                    node_id=event.node_id,
                    execution_id=event.execution_id,
                    data={
                        "audit_event_type": event.event_type.value,
                        "governance_event": event.to_dict(),
                    },
                )
                await self._event_bus.publish(agent_event)
        except Exception as e:
            logger.error(f"Failed to publish audit event to event bus: {e}")

    def log_permission_check(
        self,
        tool_name: str,
        allowed: bool,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Create and return a permission check event."""
        event_type = (
            AuditEventType.PERMISSION_GRANTED if allowed else AuditEventType.PERMISSION_DENIED
        )
        return AuditEvent(
            event_type=event_type,
            tool_name=tool_name,
            decision="allow" if allowed else "deny",
            reason=reason,
            context=context or {},
        )

    def log_risk_assessment(
        self,
        tool_name: str,
        risk_level: str,
        reasons: list[str],
        context: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Create and return a risk assessment event."""
        return AuditEvent(
            event_type=AuditEventType.RISK_ASSESSMENT,
            tool_name=tool_name,
            risk_level=risk_level,
            reason="; ".join(reasons),
            context=context or {},
        )

    def log_approval_request(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        risk_level: str,
        reason: str,
    ) -> AuditEvent:
        """Create and return an approval request event."""
        return AuditEvent(
            event_type=AuditEventType.APPROVAL_REQUESTED,
            tool_name=tool_name,
            tool_input=tool_input,
            risk_level=risk_level,
            reason=reason,
        )

    def log_approval_result(
        self,
        tool_name: str,
        approved: bool,
        actor: str,
        reason: str | None = None,
    ) -> AuditEvent:
        """Create and return an approval result event."""
        event_type = AuditEventType.APPROVAL_GRANTED if approved else AuditEventType.APPROVAL_DENIED
        return AuditEvent(
            event_type=event_type,
            tool_name=tool_name,
            decision="approved" if approved else "denied",
            actor=actor,
            reason=reason,
        )

    def log_tool_blocked(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        reason: str,
        risk_level: str | None = None,
    ) -> AuditEvent:
        """Create and return a tool blocked event."""
        return AuditEvent(
            event_type=AuditEventType.TOOL_BLOCKED,
            tool_name=tool_name,
            tool_input=tool_input,
            decision="blocked",
            reason=reason,
            risk_level=risk_level,
        )

    def log_tool_executed(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        duration_ms: int | None = None,
        success: bool = True,
    ) -> AuditEvent:
        """Create and return a tool executed event."""
        return AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTED,
            tool_name=tool_name,
            tool_input=tool_input,
            decision="success" if success else "failure",
            duration_ms=duration_ms,
        )

    def log_data_isolation_violation(
        self,
        violation_type: str,
        details: dict[str, Any],
    ) -> AuditEvent:
        """Create and return a data isolation violation event."""
        return AuditEvent(
            event_type=AuditEventType.DATA_ISOLATION_VIOLATION,
            reason=violation_type,
            context=details,
        )

    def get_events(
        self,
        event_type: AuditEventType | None = None,
        tool_name: str | None = None,
        session_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with filters."""
        events = self._events[::-1]

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get audit log statistics."""
        if not self._events:
            return {
                "total_events": 0,
                "events_by_type": {},
                "tools_blocked": 0,
                "approvals_requested": 0,
                "approvals_denied": 0,
            }

        by_type: dict[str, int] = {}
        for event in self._events:
            key = event.event_type.value
            by_type[key] = by_type.get(key, 0) + 1

        blocked = sum(1 for e in self._events if e.event_type == AuditEventType.TOOL_BLOCKED)
        approvals_requested = sum(
            1 for e in self._events if e.event_type == AuditEventType.APPROVAL_REQUESTED
        )
        approvals_denied = sum(
            1 for e in self._events if e.event_type == AuditEventType.APPROVAL_DENIED
        )

        return {
            "total_events": len(self._events),
            "events_by_type": by_type,
            "tools_blocked": blocked,
            "approvals_requested": approvals_requested,
            "approvals_denied": approvals_denied,
        }

    def clear_events(self, before: datetime | None = None) -> int:
        """Clear events from memory, optionally only before a given time."""
        if before is None:
            count = len(self._events)
            self._events.clear()
            return count

        original_count = len(self._events)
        self._events = [e for e in self._events if e.timestamp >= before]
        return original_count - len(self._events)
