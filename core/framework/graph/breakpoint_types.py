"""
Breakpoint Types - Types for human-in-the-loop approval breakpoints.

These types support the approval workflow when execution hits a breakpoint node.
The agent pauses before executing a sensitive action and waits for human approval.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalDecision(StrEnum):
    """Decision types for breakpoint approval."""

    APPROVE = "approve"
    REJECT = "reject"
    ABORT = "abort"


class BreakpointRequest(BaseModel):
    """
    Request for human approval at a breakpoint.

    Emitted when execution reaches a node marked with is_breakpoint=True
    or listed in graph.approval_nodes.
    """

    breakpoint_id: str = Field(description="Unique ID for this breakpoint request")
    node_id: str = Field(description="Node ID that triggered the breakpoint")
    node_name: str = Field(description="Human-readable node name")
    action_description: str | None = Field(
        default=None, description="Description of the action being approved"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Current memory state that will be used by the node",
    )
    tools_to_execute: list[str] = Field(
        default_factory=list,
        description="List of tools this node may call",
    )
    session_id: str | None = Field(default=None, description="Session ID for resume")
    created_at: datetime = Field(default_factory=datetime.now)

    def to_prompt(self) -> str:
        """Generate a human-readable prompt for the approval request."""
        lines = [
            "=" * 60,
            "🔔 APPROVAL REQUIRED",
            "=" * 60,
            "",
            f"Node: {self.node_name} ({self.node_id})",
        ]
        if self.action_description:
            lines.append(f"Action: {self.action_description}")

        if self.tools_to_execute:
            lines.append(f"\nTools that may be used: {', '.join(self.tools_to_execute)}")

        if self.context:
            lines.append("\n--- Current Context ---")
            for key, value in list(self.context.items())[:5]:
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                lines.append(f"  {key}: {value_str}")

        lines.extend(
            [
                "",
                "Options:",
                "  [a] Approve - Execute this node",
                "  [r] Reject  - Skip this node and continue",
                "  [x] Abort   - Stop execution entirely",
            ]
        )
        return "\n".join(lines)


class BreakpointResult(BaseModel):
    """
    Result of processing a breakpoint approval request.
    """

    breakpoint_id: str
    decision: ApprovalDecision
    reason: str | None = None
    approved_by: str = "user"
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_approved(self) -> bool:
        """Check if the decision was to approve."""
        return self.decision == ApprovalDecision.APPROVE

    @property
    def is_rejected(self) -> bool:
        """Check if the decision was to reject."""
        return self.decision == ApprovalDecision.REJECT

    @property
    def is_aborted(self) -> bool:
        """Check if the decision was to abort."""
        return self.decision == ApprovalDecision.ABORT

    @classmethod
    def approve(cls, breakpoint_id: str, reason: str | None = None) -> "BreakpointResult":
        """Create an approval result."""
        return cls(
            breakpoint_id=breakpoint_id,
            decision=ApprovalDecision.APPROVE,
            reason=reason,
        )

    @classmethod
    def reject(cls, breakpoint_id: str, reason: str | None = None) -> "BreakpointResult":
        """Create a rejection result."""
        return cls(
            breakpoint_id=breakpoint_id,
            decision=ApprovalDecision.REJECT,
            reason=reason,
        )

    @classmethod
    def abort(cls, breakpoint_id: str, reason: str | None = None) -> "BreakpointResult":
        """Create an abort result."""
        return cls(
            breakpoint_id=breakpoint_id,
            decision=ApprovalDecision.ABORT,
            reason=reason,
        )
