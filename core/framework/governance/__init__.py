"""
Trust & Governance Layer for Autonomous Agents

This module provides a first-class governance architecture for Hive agents,
enabling enterprise-grade trust, auditability, and control over autonomous behavior.

Components:
- GuardrailConfig: Configuration for governance policies
- PermissionPolicy: Deterministic tool-level access controls
- RiskClassifier: Risk assessment for tool actions
- AuditLogger: Comprehensive audit trail logging
- GuardrailEngine: Central orchestration engine
- DataIsolationPolicy: Per-session/agent data boundaries

Usage:
    from framework.governance import GuardrailConfig, GuardrailEngine

    # Create configuration
    config = GuardrailConfig(
        enabled=True,
        permission_policy=PermissionPolicy(
            allowed_tools=["web_search", "email_send"],
            blocked_tools=["file_delete", "shell_execute"],
        ),
        risk_policy=RiskPolicy(
            high_risk_tools=["payment_process", "data_export"],
            approval_required_for_high_risk=True,
        ),
    )

    # Create and attach engine
    guardrail = GuardrailEngine(config, event_bus)
    await guardrail.initialize()

    # Evaluate tool calls
    result = await guardrail.evaluate_tool_call(tool_use)
    if result.blocked:
        return ToolResult(..., is_error=True)
"""

from framework.governance.config import (
    AuditConfig,
    DataIsolationConfig,
    GuardrailConfig,
    RiskLevel,
    RiskPolicy,
)
from framework.governance.engine import GuardrailEngine, GuardrailResult
from framework.governance.permissions import (
    PermissionPolicy,
    PermissionRule,
    ToolPermission,
)
from framework.governance.risk import RiskClassifier, RiskContext

__all__ = [
    "GuardrailConfig",
    "GuardrailEngine",
    "GuardrailResult",
    "PermissionPolicy",
    "PermissionRule",
    "ToolPermission",
    "RiskLevel",
    "RiskPolicy",
    "RiskClassifier",
    "RiskContext",
    "AuditConfig",
    "DataIsolationConfig",
]
