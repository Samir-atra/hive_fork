"""Business-friendly intervention models for Human-in-the-loop."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class InterventionStatus(StrEnum):
    """Status of an intervention request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class AuditLog(BaseModel):
    """Audit log entry for an intervention state change."""

    timestamp: datetime = Field(default_factory=datetime.now)
    action: str = Field(description="Action taken (e.g. created, approved).")
    actor: str = Field(default="system", description="User or system performing the action.")
    details: str | None = Field(default=None, description="Optional reasoning or details.")


class Intervention(BaseModel):
    """
    A business-friendly wrapper around an agent intervention (e.g. human-in-the-loop).

    Translates technical node decisions into a business-friendly format with an audit trail.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(description="The worker session this intervention applies to.")
    node_id: str = Field(description="The technical node ID requesting intervention.")
    status: InterventionStatus = Field(default=InterventionStatus.PENDING)

    # Business context
    summary: str = Field(description="Plain English summary of the intervention.")
    business_context: str = Field(description="Business context or reasoning.")
    technical_decision: str = Field(description="Technical details of the agent's decision.")

    audit_trail: list[AuditLog] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    timeout_hours: int | None = Field(default=None, description="Hours until auto-escalation.")

    def approve(self, actor: str = "system", reason: str | None = None) -> None:
        """Approve the intervention."""
        self.status = InterventionStatus.APPROVED
        self.updated_at = datetime.now()
        self.audit_trail.append(AuditLog(action="approved", actor=actor, details=reason))

    def reject(self, actor: str = "system", reason: str | None = None) -> None:
        """Reject the intervention."""
        self.status = InterventionStatus.REJECTED
        self.updated_at = datetime.now()
        self.audit_trail.append(AuditLog(action="rejected", actor=actor, details=reason))

    def escalate(self, actor: str = "system", reason: str | None = None) -> None:
        """Escalate the intervention."""
        self.status = InterventionStatus.ESCALATED
        self.updated_at = datetime.now()
        self.audit_trail.append(AuditLog(action="escalated", actor=actor, details=reason))
