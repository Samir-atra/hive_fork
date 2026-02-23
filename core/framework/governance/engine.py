"""
Guardrail Engine - Central Orchestration for Governance

The GuardrailEngine coordinates all governance components:
- Permission evaluation
- Risk classification
- Approval workflows
- Audit logging
- Data isolation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from framework.governance.audit import AuditEvent, AuditEventType, AuditLogger
from framework.governance.config import (
    ApprovalMode,
    DataIsolationConfig,
    GuardrailConfig,
    RiskLevel,
)
from framework.governance.permissions import PermissionCheckResult, PermissionEvaluator
from framework.governance.risk import RiskAssessment, RiskClassifier, RiskContext

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    """A request for human approval of a tool call."""

    request_id: str
    tool_name: str
    tool_input: dict[str, Any]
    risk_level: RiskLevel
    risk_reasons: list[str]
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 300
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "risk_level": self.risk_level.value,
            "risk_reasons": self.risk_reasons,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "status": self.status,
        }


@dataclass
class GuardrailResult:
    """Result of guardrail evaluation."""

    allowed: bool
    tool_name: str
    tool_use_id: str
    reason: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approval_request: ApprovalRequest | None = None
    permission_result: PermissionCheckResult | None = None
    risk_assessment: RiskAssessment | None = None
    blocked: bool = False
    audit_event: AuditEvent | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tool_name": self.tool_name,
            "tool_use_id": self.tool_use_id,
            "reason": self.reason,
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
            "approval_request": self.approval_request.to_dict() if self.approval_request else None,
            "permission_result": self.permission_result.to_dict()
            if self.permission_result
            else None,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "blocked": self.blocked,
        }


class ApprovalCallback:
    """Interface for approval callbacks."""

    async def request_approval(self, request: ApprovalRequest) -> bool:
        """Request approval and wait for response."""
        raise NotImplementedError

    async def check_approval_status(self, request_id: str) -> str:
        """Check status of an approval request."""
        raise NotImplementedError


class GuardrailEngine:
    """
    Central governance orchestration engine.

    Coordinates:
    - Permission evaluation
    - Risk classification
    - Approval workflows
    - Audit logging
    - Data isolation enforcement

    Usage:
        config = GuardrailConfig.strict()
        engine = GuardrailEngine(config, event_bus)

        # Evaluate a tool call
        result = await engine.evaluate_tool_call(tool_use, context)
        if result.blocked:
            return error_response

        if result.requires_approval:
            approved = await engine.request_approval(result.approval_request)
            if not approved:
                return blocked_response

        # Execute the tool
        return await execute_tool(tool_use)
    """

    def __init__(
        self,
        config: GuardrailConfig,
        event_bus: Any | None = None,
        approval_callback: ApprovalCallback | None = None,
    ):
        self.config = config
        self._event_bus = event_bus

        self._permission_evaluator = PermissionEvaluator(config.permission_policy)
        self._risk_classifier = RiskClassifier(config.risk_policy)
        self._audit_logger = AuditLogger(config.audit_config, event_bus)

        self._approval_callback = approval_callback
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_decisions: dict[str, bool] = {}
        self._approval_counter = 0

        self._initialized = False
        self._call_history: list[dict[str, Any]] = []
        self._max_history = 100

    async def initialize(self) -> None:
        """Initialize the guardrail engine."""
        if self._initialized:
            return

        if self._event_bus:
            from framework.runtime.event_bus import EventType

            self._event_bus.subscribe(
                event_types=[EventType.TOOL_CALL_STARTED],
                handler=self._on_tool_call_started,
            )
            self._event_bus.subscribe(
                event_types=[EventType.TOOL_CALL_COMPLETED],
                handler=self._on_tool_call_completed,
            )

        self._initialized = True
        logger.info(f"GuardrailEngine initialized with config: {self.config.name}")

    async def _on_tool_call_started(self, event: Any) -> None:
        """Handle tool call started event."""
        pass

    async def _on_tool_call_completed(self, event: Any) -> None:
        """Handle tool call completed event."""
        pass

    async def evaluate_tool_call(
        self,
        tool_use: Any,
        context: dict[str, Any] | None = None,
    ) -> GuardrailResult:
        """
        Evaluate a tool call against governance policies.

        Args:
            tool_use: The ToolUse object to evaluate
            context: Additional context for evaluation

        Returns:
            GuardrailResult with evaluation outcome
        """
        if not self.config.enabled:
            return GuardrailResult(
                allowed=True,
                tool_name=tool_use.name,
                tool_use_id=tool_use.id,
                reason="Guardrail is disabled",
            )

        tool_name = tool_use.name
        tool_input = getattr(tool_use, "input", {}) or {}
        tool_use_id = getattr(tool_use, "id", "unknown")

        risk_context = self._build_risk_context(tool_name, tool_input, context)
        risk_assessment = self._risk_classifier.assess_risk(tool_name, tool_input, risk_context)

        if self.config.audit_config.log_risk_assessments:
            audit_event = self._audit_logger.log_risk_assessment(
                tool_name,
                risk_assessment.risk_level.value,
                risk_assessment.reasons,
                {"context": context},
            )
            await self._audit_logger.log_event(audit_event)

        permission_result = self._permission_evaluator.check_permission(
            tool_name, tool_input, context
        )

        if self.config.audit_config.log_permission_checks:
            audit_event = self._audit_logger.log_permission_check(
                tool_name,
                permission_result.allowed,
                permission_result.reason,
                {"context": context},
            )
            await self._audit_logger.log_event(audit_event)

        if not permission_result.allowed:
            audit_event = self._audit_logger.log_tool_blocked(
                tool_name,
                tool_input,
                permission_result.reason,
                risk_assessment.risk_level.value,
            )
            await self._audit_logger.log_event(audit_event)

            return GuardrailResult(
                allowed=False,
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                reason=permission_result.reason,
                risk_level=risk_assessment.risk_level,
                blocked=True,
                permission_result=permission_result,
                risk_assessment=risk_assessment,
                audit_event=audit_event,
            )

        requires_approval = self._check_approval_required(
            tool_name, risk_assessment, permission_result
        )

        if requires_approval:
            approval_request = await self._create_approval_request(
                tool_name, tool_input, risk_assessment, context
            )

            return GuardrailResult(
                allowed=True,
                tool_name=tool_name,
                tool_use_id=tool_use_id,
                reason="Requires approval",
                risk_level=risk_assessment.risk_level,
                requires_approval=True,
                approval_request=approval_request,
                permission_result=permission_result,
                risk_assessment=risk_assessment,
            )

        self._record_call(tool_name, tool_input, context)

        return GuardrailResult(
            allowed=True,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            reason="Tool call allowed",
            risk_level=risk_assessment.risk_level,
            permission_result=permission_result,
            risk_assessment=risk_assessment,
        )

    def _build_risk_context(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> RiskContext:
        """Build risk context for assessment."""
        ctx = context or {}
        return RiskContext(
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=ctx.get("session_id"),
            agent_id=ctx.get("agent_id"),
            node_id=ctx.get("node_id"),
            execution_id=ctx.get("execution_id"),
            user_id=ctx.get("user_id"),
            environment=ctx.get("environment", "development"),
            previous_calls=self._call_history[-10:],
        )

    def _check_approval_required(
        self,
        tool_name: str,
        risk_assessment: RiskAssessment,
        permission_result: PermissionCheckResult,
    ) -> bool:
        """Check if approval is required for this tool call."""
        if risk_assessment.requires_approval:
            return True

        if permission_result.permission and permission_result.permission.requires_approval:
            approval_mode = self.config.risk_policy.approval_mode

            if approval_mode == ApprovalMode.ALWAYS:
                return True
            elif approval_mode == ApprovalMode.FIRST_TIME:
                return self._permission_evaluator.is_first_use(tool_name)

        return False

    async def _create_approval_request(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        risk_assessment: RiskAssessment,
        context: dict[str, Any] | None,
    ) -> ApprovalRequest:
        """Create an approval request."""
        self._approval_counter += 1
        request_id = f"approval_{self._approval_counter}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        request = ApprovalRequest(
            request_id=request_id,
            tool_name=tool_name,
            tool_input=tool_input,
            risk_level=risk_assessment.risk_level,
            risk_reasons=risk_assessment.reasons,
            context=context or {},
            timeout_seconds=self.config.risk_policy.approval_timeout_seconds,
        )

        self._pending_approvals[request_id] = request

        audit_event = self._audit_logger.log_approval_request(
            tool_name,
            tool_input,
            risk_assessment.risk_level.value,
            "; ".join(risk_assessment.reasons),
        )
        audit_event.metadata["request_id"] = request_id
        await self._audit_logger.log_event(audit_event)

        return request

    async def request_approval(self, request: ApprovalRequest) -> bool:
        """
        Request human approval for a tool call.

        Args:
            request: The approval request

        Returns:
            True if approved, False if denied or timed out
        """
        if request.request_id in self._approval_decisions:
            return self._approval_decisions[request.request_id]

        if self._approval_callback:
            try:
                approved = await asyncio.wait_for(
                    self._approval_callback.request_approval(request),
                    timeout=request.timeout_seconds,
                )

                self._approval_decisions[request.request_id] = approved
                self._pending_approvals.pop(request.request_id, None)

                audit_event = self._audit_logger.log_approval_result(
                    request.tool_name,
                    approved,
                    "approval_callback",
                )
                audit_event.metadata["request_id"] = request.request_id
                await self._audit_logger.log_event(audit_event)

                return approved

            except asyncio.TimeoutError:
                self._pending_approvals.pop(request.request_id, None)

                audit_event = self._audit_logger.log_approval_result(
                    request.tool_name,
                    False,
                    "system",
                    "Approval request timed out",
                )
                audit_event.metadata["request_id"] = request.request_id
                await self._audit_logger.log_event(audit_event)

                return False

        logger.warning(
            f"No approval callback configured for request {request.request_id}, defaulting to deny"
        )
        return False

    def set_approval_decision(self, request_id: str, approved: bool) -> None:
        """Manually set an approval decision."""
        self._approval_decisions[request_id] = approved
        if request_id in self._pending_approvals:
            request = self._pending_approvals.pop(request_id)
            request.status = "approved" if approved else "denied"

    def set_approval_callback(self, callback: ApprovalCallback) -> None:
        """Set the approval callback handler."""
        self._approval_callback = callback

    async def check_data_access(
        self,
        key: str,
        operation: str,
        context: dict[str, Any] | None,
    ) -> tuple[bool, str | None]:
        """
        Check if data access is allowed by data isolation policy.

        Args:
            key: The data key being accessed
            operation: "read" or "write"
            context: Context including session_id, agent_id

        Returns:
            Tuple of (allowed, reason_if_blocked)
        """
        if not self.config.data_isolation.enabled:
            return True, None

        config = self.config.data_isolation

        import re

        for pattern in config.blocked_data_patterns:
            if re.search(pattern, key, re.IGNORECASE):
                audit_event = self._audit_logger.log_data_isolation_violation(
                    "blocked_pattern",
                    {"key": key, "pattern": pattern, "operation": operation},
                )
                await self._audit_logger.log_event(audit_event)
                return False, f"Key '{key}' matches blocked pattern"

        ctx = context or {}

        if config.enforce_session_isolation:
            current_session = ctx.get("session_id")
            key_session = ctx.get("key_session_id")

            if key_session and current_session and key_session != current_session:
                if key not in config.allowed_shared_keys:
                    if config.cross_session_access_mode == "deny":
                        audit_event = self._audit_logger.log_data_isolation_violation(
                            "cross_session_access",
                            {
                                "key": key,
                                "current_session": current_session,
                                "key_session": key_session,
                            },
                        )
                        await self._audit_logger.log_event(audit_event)
                        return False, "Cross-session access denied"

        return True, None

    def _record_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> None:
        """Record a tool call in history."""
        self._call_history.append(
            {
                "tool_name": tool_name,
                "input_keys": list(tool_input.keys()) if tool_input else [],
                "context_keys": list(context.keys()) if context else [],
                "timestamp": datetime.now().isoformat(),
            }
        )

        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history :]

    def get_statistics(self) -> dict[str, Any]:
        """Get guardrail engine statistics."""
        return {
            "config_name": self.config.name,
            "config_enabled": self.config.enabled,
            "pending_approvals": len(self._pending_approvals),
            "total_approval_decisions": len(self._approval_decisions),
            "call_history_size": len(self._call_history),
            "permission_stats": self._permission_evaluator.get_stats(),
            "audit_stats": self._audit_logger.get_statistics(),
        }

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        return list(self._pending_approvals.values())

    async def shutdown(self) -> None:
        """Shutdown the guardrail engine."""
        self._pending_approvals.clear()
        self._initialized = False
        logger.info("GuardrailEngine shutdown complete")


def create_wrapped_executor(
    original_executor: Callable,
    guardrail: GuardrailEngine,
    context: dict[str, Any] | None = None,
) -> Callable:
    """
    Create a tool executor wrapped with guardrail checks.

    Args:
        original_executor: The original tool executor function
        guardrail: The guardrail engine to use
        context: Additional context for guardrail evaluation

    Returns:
        Wrapped executor function
    """

    async def wrapped_executor(tool_use: Any) -> Any:
        result = await guardrail.evaluate_tool_call(tool_use, context)

        if result.blocked:
            from framework.llm.provider import ToolResult

            return ToolResult(
                tool_use_id=tool_use.id,
                content=f'{{"error": "Tool call blocked by guardrail: {result.reason}"}}',
                is_error=True,
            )

        if result.requires_approval and result.approval_request:
            approved = await guardrail.request_approval(result.approval_request)
            if not approved:
                from framework.llm.provider import ToolResult

                return ToolResult(
                    tool_use_id=tool_use.id,
                    content='{"error": "Tool call was not approved"}',
                    is_error=True,
                )

        return original_executor(tool_use)

    return wrapped_executor
