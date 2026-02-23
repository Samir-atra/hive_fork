"""
Unit tests for the Governance Layer

Tests for:
- GuardrailConfig
- PermissionPolicy and PermissionEvaluator
- RiskClassifier
- AuditLogger
- GuardrailEngine
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from framework.governance import (
    GuardrailConfig,
    GuardrailEngine,
    GuardrailResult,
    PermissionPolicy,
    PermissionRule,
    ToolPermission,
    RiskLevel,
    RiskPolicy,
    RiskClassifier,
    RiskContext,
    AuditConfig,
    DataIsolationConfig,
)
from framework.governance.config import ApprovalMode
from framework.governance.permissions import PermissionEvaluator, PermissionCheckResult
from framework.governance.risk import RiskAssessment
from framework.governance.audit import AuditLogger, AuditEventType, AuditEvent
from framework.llm.provider import ToolUse


class TestGuardrailConfig:
    """Tests for GuardrailConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GuardrailConfig()

        assert config.enabled is True
        assert config.name == "default"
        assert config.fail_closed is True
        assert config.permission_policy.enabled is True
        assert config.risk_policy.enabled is True
        assert config.audit_config.enabled is True

    def test_strict_config(self):
        """Test strict configuration preset."""
        config = GuardrailConfig.strict()

        assert config.enabled is True
        assert config.name == "strict"
        assert config.permission_policy.default_allowed is False
        assert config.risk_policy.approval_mode == ApprovalMode.ALWAYS
        assert config.data_isolation.enforce_session_isolation is True

    def test_permissive_config(self):
        """Test permissive configuration preset."""
        config = GuardrailConfig.permissive()

        assert config.enabled is True
        assert config.name == "permissive"
        assert config.permission_policy.default_allowed is True
        assert config.risk_policy.approval_mode == ApprovalMode.NEVER
        assert config.data_isolation.enabled is False

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = GuardrailConfig.strict()
        data = original.to_dict()
        restored = GuardrailConfig.from_dict(data)

        assert restored.enabled == original.enabled
        assert restored.name == original.name
        assert (
            restored.permission_policy.default_allowed == original.permission_policy.default_allowed
        )
        assert restored.risk_policy.approval_mode == original.risk_policy.approval_mode


class TestPermissionPolicy:
    """Tests for PermissionPolicy."""

    def test_default_policy(self):
        """Test default permission policy."""
        policy = PermissionPolicy()

        assert policy.enabled is True
        assert policy.default_allowed is True
        assert len(policy.allowed_tools) == 0
        assert len(policy.blocked_tools) == 0

    def test_tool_allowed_by_default(self):
        """Test tool allowed by default policy."""
        policy = PermissionPolicy(default_allowed=True)

        assert policy.is_tool_allowed("any_tool") is True

    def test_tool_blocked_by_default(self):
        """Test tool blocked by default policy."""
        policy = PermissionPolicy(default_allowed=False)

        assert policy.is_tool_allowed("any_tool") is False

    def test_allowed_list(self):
        """Test allowed tools list."""
        policy = PermissionPolicy(
            allowed_tools=["web_search", "email_send"],
            default_allowed=False,
        )

        assert policy.is_tool_allowed("web_search") is True
        assert policy.is_tool_allowed("email_send") is True
        assert policy.is_tool_allowed("file_delete") is False

    def test_blocked_list(self):
        """Test blocked tools list."""
        policy = PermissionPolicy(
            blocked_tools=["file_delete", "shell_execute"],
            default_allowed=True,
        )

        assert policy.is_tool_allowed("web_search") is True
        assert policy.is_tool_allowed("file_delete") is False
        assert policy.is_tool_allowed("shell_execute") is False

    def test_tool_permissions_override(self):
        """Test per-tool permission overrides."""
        policy = PermissionPolicy(
            tool_permissions={
                "sensitive_tool": ToolPermission(
                    tool_name="sensitive_tool",
                    allowed=False,
                    risk_level=RiskLevel.HIGH,
                )
            },
            default_allowed=True,
        )

        assert policy.is_tool_allowed("sensitive_tool") is False
        assert policy.is_tool_allowed("other_tool") is True


class TestPermissionEvaluator:
    """Tests for PermissionEvaluator."""

    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        policy = PermissionPolicy()
        evaluator = PermissionEvaluator(policy)

        assert evaluator.policy == policy

    def test_check_permission_allowed(self):
        """Test permission check for allowed tool."""
        policy = PermissionPolicy(
            allowed_tools=["web_search"],
            default_allowed=False,
        )
        evaluator = PermissionEvaluator(policy)

        result = evaluator.check_permission("web_search")

        assert result.allowed is True
        assert result.tool_name == "web_search"

    def test_check_permission_blocked(self):
        """Test permission check for blocked tool."""
        policy = PermissionPolicy(
            blocked_tools=["file_delete"],
            default_allowed=True,
        )
        evaluator = PermissionEvaluator(policy)

        result = evaluator.check_permission("file_delete")

        assert result.allowed is False
        assert "not allowed" in result.reason.lower()

    def test_parameter_restrictions(self):
        """Test parameter-level restrictions."""
        policy = PermissionPolicy(
            tool_permissions={
                "api_call": ToolPermission(
                    tool_name="api_call",
                    allowed=True,
                    allowed_parameters={"method": ["GET", "POST"]},
                    blocked_parameter_values={"endpoint": ["/admin", "/delete"]},
                )
            }
        )
        evaluator = PermissionEvaluator(policy)

        result = evaluator.check_permission("api_call", {"method": "GET"})
        assert result.allowed is True

        result = evaluator.check_permission("api_call", {"method": "DELETE"})
        assert result.allowed is False

        result = evaluator.check_permission("api_call", {"endpoint": "/admin"})
        assert result.allowed is False

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        policy = PermissionPolicy(
            tool_permissions={
                "limited_tool": ToolPermission(
                    tool_name="limited_tool",
                    allowed=True,
                    rate_limit_per_minute=2,
                )
            }
        )
        evaluator = PermissionEvaluator(policy)

        result1 = evaluator.check_permission("limited_tool")
        assert result1.allowed is True

        result2 = evaluator.check_permission("limited_tool")
        assert result2.allowed is True

        result3 = evaluator.check_permission("limited_tool")
        assert result3.allowed is False
        assert "rate limit" in result3.reason.lower()


class TestRiskClassifier:
    """Tests for RiskClassifier."""

    def test_classifier_initialization(self):
        """Test classifier initialization."""
        policy = RiskPolicy()
        classifier = RiskClassifier(policy)

        assert classifier.policy == policy

    def test_low_risk_tool(self):
        """Test classification of low-risk tool."""
        policy = RiskPolicy()
        classifier = RiskClassifier(policy)

        assessment = classifier.assess_risk("get_weather", {"location": "SF"})

        assert assessment.risk_level == RiskLevel.LOW

    def test_high_risk_tool_by_name(self):
        """Test classification of high-risk tool by name."""
        policy = RiskPolicy(high_risk_tools=["payment_process"])
        classifier = RiskClassifier(policy)

        assessment = classifier.assess_risk("payment_process", {"amount": 100})

        assert assessment.risk_level == RiskLevel.HIGH
        assert any("high risk" in r.lower() for r in assessment.reasons)

    def test_critical_risk_tool_by_name(self):
        """Test classification of critical-risk tool by name."""
        policy = RiskPolicy(critical_risk_tools=["admin_delete_all"])
        classifier = RiskClassifier(policy)

        assessment = classifier.assess_risk("admin_delete_all", {})

        assert assessment.risk_level == RiskLevel.CRITICAL

    def test_risk_by_keyword(self):
        """Test risk classification by keyword detection."""
        policy = RiskPolicy()
        classifier = RiskClassifier(policy)

        assessment = classifier.assess_risk("delete_records", {})

        assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]

    def test_risk_by_parameter(self):
        """Test risk classification by parameter analysis."""
        policy = RiskPolicy()
        classifier = RiskClassifier(policy)

        assessment = classifier.assess_risk(
            "api_call", {"password": "secret123", "action": "delete"}
        )

        assert len(assessment.reasons) > 0
        assert any(
            "sensitive" in r.lower() or "destructive" in r.lower() for r in assessment.reasons
        )

    def test_environment_risk(self):
        """Test environment-aware risk assessment."""
        policy = RiskPolicy()
        classifier = RiskClassifier(policy)

        context = RiskContext(tool_name="deploy", environment="production")
        assessment = classifier.assess_risk("deploy", {}, context)

        assert any("production" in r.lower() for r in assessment.reasons)

    def test_approval_requirement(self):
        """Test approval requirement based on risk level."""
        policy = RiskPolicy(
            risk_threshold_for_approval=RiskLevel.HIGH,
            approval_mode=ApprovalMode.THRESHOLD,
        )
        classifier = RiskClassifier(policy)

        low_assessment = classifier.assess_risk("safe_tool", {})
        assert low_assessment.requires_approval is False

        policy = RiskPolicy(
            high_risk_tools=["risky_tool"],
            risk_threshold_for_approval=RiskLevel.HIGH,
            approval_mode=ApprovalMode.THRESHOLD,
        )
        classifier = RiskClassifier(policy)
        high_assessment = classifier.assess_risk("risky_tool", {})
        assert high_assessment.requires_approval is True


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_logger_initialization(self):
        """Test logger initialization."""
        config = AuditConfig()
        logger = AuditLogger(config)

        assert logger.config == config

    @pytest.mark.asyncio
    async def test_log_event(self):
        """Test logging an event."""
        config = AuditConfig(log_to_file=False, log_to_event_bus=False)
        logger = AuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_DENIED,
            tool_name="blocked_tool",
            reason="Not allowed",
        )

        await logger.log_event(event)

        events = logger.get_events()
        assert len(events) == 1
        assert events[0].tool_name == "blocked_tool"

    @pytest.mark.asyncio
    async def test_sensitive_data_redaction(self):
        """Test sensitive data redaction."""
        config = AuditConfig(
            log_to_file=False,
            log_to_event_bus=False,
            include_sensitive_params=False,
        )
        logger = AuditLogger(config)

        event = AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTED,
            tool_name="api_call",
            tool_input={"password": "secret123", "api_key": "key123", "safe_param": "value"},
        )

        await logger.log_event(event)

        logged_event = logger.get_events()[0]
        assert logged_event.tool_input["password"] == "[REDACTED]"
        assert logged_event.tool_input["api_key"] == "[REDACTED]"
        assert logged_event.tool_input["safe_param"] == "value"

    @pytest.mark.asyncio
    async def test_event_filtering(self):
        """Test event filtering by type."""
        config = AuditConfig(
            log_to_file=False,
            log_to_event_bus=False,
            log_permission_checks=True,
            log_tool_calls=False,
        )
        logger = AuditLogger(config)

        perm_event = AuditEvent(
            event_type=AuditEventType.PERMISSION_GRANTED,
            tool_name="tool1",
        )
        tool_event = AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTED,
            tool_name="tool2",
        )

        await logger.log_event(perm_event)
        await logger.log_event(tool_event)

        events = logger.get_events()
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.PERMISSION_GRANTED

    def test_get_statistics(self):
        """Test statistics generation."""
        config = AuditConfig(log_to_file=False, log_to_event_bus=False)
        logger = AuditLogger(config)

        logger._events = [
            AuditEvent(event_type=AuditEventType.TOOL_BLOCKED, tool_name="t1"),
            AuditEvent(event_type=AuditEventType.TOOL_BLOCKED, tool_name="t2"),
            AuditEvent(event_type=AuditEventType.APPROVAL_DENIED, tool_name="t3"),
        ]

        stats = logger.get_statistics()

        assert stats["total_events"] == 3
        assert stats["tools_blocked"] == 2
        assert stats["approvals_denied"] == 1


class TestGuardrailEngine:
    """Tests for GuardrailEngine."""

    def test_engine_initialization(self):
        """Test engine initialization."""
        config = GuardrailConfig()
        engine = GuardrailEngine(config)

        assert engine.config == config
        assert engine._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test engine initialization."""
        config = GuardrailConfig()
        engine = GuardrailEngine(config)

        await engine.initialize()

        assert engine._initialized is True

    @pytest.mark.asyncio
    async def test_evaluate_allowed_tool(self):
        """Test evaluation of allowed tool."""
        config = GuardrailConfig.permissive()
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="web_search", input={"query": "test"})

        result = await engine.evaluate_tool_call(tool_use)

        assert result.allowed is True
        assert result.blocked is False

    @pytest.mark.asyncio
    async def test_evaluate_blocked_tool(self):
        """Test evaluation of blocked tool."""
        config = GuardrailConfig(
            permission_policy=PermissionPolicy(
                blocked_tools=["file_delete"],
                default_allowed=True,
            )
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="file_delete", input={"path": "/data"})

        result = await engine.evaluate_tool_call(tool_use)

        assert result.allowed is False
        assert result.blocked is True

    @pytest.mark.asyncio
    async def test_approval_required(self):
        """Test approval requirement flow."""
        config = GuardrailConfig(
            risk_policy=RiskPolicy(
                high_risk_tools=["payment_process"],
                approval_mode=ApprovalMode.ALWAYS,
            ),
            permission_policy=PermissionPolicy(default_allowed=True),
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="payment_process", input={"amount": 100})

        result = await engine.evaluate_tool_call(tool_use)

        assert result.requires_approval is True
        assert result.approval_request is not None

    @pytest.mark.asyncio
    async def test_disabled_guardrail(self):
        """Test disabled guardrail allows everything."""
        config = GuardrailConfig(enabled=False)
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="dangerous_tool", input={})

        result = await engine.evaluate_tool_call(tool_use)

        assert result.allowed is True
        assert "disabled" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_data_access_check(self):
        """Test data access isolation check."""
        config = GuardrailConfig(
            data_isolation=DataIsolationConfig(
                enabled=True,
                blocked_data_patterns=[r"\.env", r"credentials"],
            )
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        allowed, reason = await engine.check_data_access(
            "/app/.env", "read", {"session_id": "session1"}
        )

        assert allowed is False
        assert "blocked pattern" in reason.lower()

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test statistics retrieval."""
        config = GuardrailConfig()
        engine = GuardrailEngine(config)
        await engine.initialize()

        stats = engine.get_statistics()

        assert "config_name" in stats
        assert "pending_approvals" in stats
        assert stats["config_enabled"] is True


class TestApprovalWorkflow:
    """Tests for approval workflow."""

    @pytest.mark.asyncio
    async def test_manual_approval(self):
        """Test manual approval setting."""
        config = GuardrailConfig(
            risk_policy=RiskPolicy(
                high_risk_tools=["sensitive_action"],
                approval_mode=ApprovalMode.ALWAYS,
            ),
            permission_policy=PermissionPolicy(default_allowed=True),
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="sensitive_action", input={})
        result = await engine.evaluate_tool_call(tool_use)

        assert result.requires_approval is True

        engine.set_approval_decision(result.approval_request.request_id, True)

        approved = await engine.request_approval(result.approval_request)
        assert approved is True

    @pytest.mark.asyncio
    async def test_approval_timeout(self):
        """Test approval timeout handling."""
        config = GuardrailConfig(
            risk_policy=RiskPolicy(
                high_risk_tools=["slow_action"],
                approval_mode=ApprovalMode.ALWAYS,
                approval_timeout_seconds=1,
            ),
            permission_policy=PermissionPolicy(default_allowed=True),
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        tool_use = ToolUse(id="call1", name="slow_action", input={})
        result = await engine.evaluate_tool_call(tool_use)

        result.approval_request.timeout_seconds = 1

        class SlowCallback:
            async def request_approval(self, request):
                await asyncio.sleep(5)
                return True

        engine.set_approval_callback(SlowCallback())

        approved = await engine.request_approval(result.approval_request)
        assert approved is False


class TestWrappedExecutor:
    """Tests for wrapped executor functionality."""

    @pytest.mark.asyncio
    async def test_wrapped_executor_blocks(self):
        """Test that wrapped executor blocks disallowed tools."""
        from framework.governance.engine import create_wrapped_executor
        from framework.llm.provider import ToolResult

        config = GuardrailConfig(
            permission_policy=PermissionPolicy(
                blocked_tools=["blocked_tool"],
                default_allowed=True,
            )
        )
        engine = GuardrailEngine(config)
        await engine.initialize()

        def original_executor(tool_use):
            return ToolResult(tool_use_id=tool_use.id, content="{}")

        wrapped = create_wrapped_executor(original_executor, engine)

        tool_use = ToolUse(id="call1", name="blocked_tool", input={})
        result = await wrapped(tool_use)

        assert result.is_error is True
        assert "blocked" in result.content.lower()

    @pytest.mark.asyncio
    async def test_wrapped_executor_allows(self):
        """Test that wrapped executor allows permitted tools."""
        from framework.governance.engine import create_wrapped_executor
        from framework.llm.provider import ToolResult

        config = GuardrailConfig.permissive()
        engine = GuardrailEngine(config)
        await engine.initialize()

        def original_executor(tool_use):
            return ToolResult(tool_use_id=tool_use.id, content='{"success": true}')

        wrapped = create_wrapped_executor(original_executor, engine)

        tool_use = ToolUse(id="call1", name="allowed_tool", input={})
        result = await wrapped(tool_use)

        assert result.is_error is False
        assert "success" in result.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
