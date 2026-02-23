"""
Guardrail Configuration Models

Defines the configuration structure for the governance layer including:
- Permission policies (tool allowlists/blocklists)
- Risk policies (risk levels, approval requirements)
- Audit configuration (logging destinations, retention)
- Data isolation settings
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RiskLevel(StrEnum):
    """Risk levels for tool actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalMode(StrEnum):
    """Approval modes for high-risk actions."""

    NEVER = "never"
    ALWAYS = "always"
    FIRST_TIME = "first_time"
    THRESHOLD = "threshold"


@dataclass
class ToolPermission:
    """Permission configuration for a specific tool."""

    tool_name: str
    allowed: bool = True
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approval_timeout_seconds: int = 300
    max_retries: int = 3
    allowed_parameters: dict[str, Any] | None = None
    blocked_parameter_values: dict[str, list[Any]] | None = None
    rate_limit_per_minute: int | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "allowed": self.allowed,
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
            "approval_timeout_seconds": self.approval_timeout_seconds,
            "max_retries": self.max_retries,
            "allowed_parameters": self.allowed_parameters,
            "blocked_parameter_values": self.blocked_parameter_values,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "description": self.description,
        }


@dataclass
class PermissionRule:
    """A rule for permission evaluation."""

    name: str
    condition: str
    action: str
    priority: int = 100
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "action": self.action,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class PermissionPolicy:
    """
    Deterministic permission policy for tool access control.

    Supports:
    - Tool allowlists/blocklists
    - Per-tool permission configurations
    - Parameter-level restrictions
    - Rate limiting
    """

    enabled: bool = True

    allowed_tools: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)

    tool_permissions: dict[str, ToolPermission] = field(default_factory=dict)

    default_allowed: bool = True
    default_risk_level: RiskLevel = RiskLevel.LOW

    rules: list[PermissionRule] = field(default_factory=list)

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed by policy."""
        if tool_name in self.tool_permissions:
            return self.tool_permissions[tool_name].allowed

        if self.blocked_tools and tool_name in self.blocked_tools:
            return False

        if self.allowed_tools:
            return tool_name in self.allowed_tools

        return self.default_allowed

    def get_tool_permission(self, tool_name: str) -> ToolPermission:
        """Get permission configuration for a tool."""
        if tool_name in self.tool_permissions:
            return self.tool_permissions[tool_name]

        return ToolPermission(
            tool_name=tool_name,
            allowed=self.is_tool_allowed(tool_name),
            risk_level=self.default_risk_level,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "tool_permissions": {k: v.to_dict() for k, v in self.tool_permissions.items()},
            "default_allowed": self.default_allowed,
            "default_risk_level": self.default_risk_level.value,
            "rules": [r.to_dict() for r in self.rules],
        }


@dataclass
class RiskPolicy:
    """
    Risk classification and approval policy.

    Defines how risk is assessed and what approval requirements exist.
    """

    enabled: bool = True

    high_risk_tools: list[str] = field(default_factory=list)
    critical_risk_tools: list[str] = field(default_factory=list)

    high_risk_keywords: list[str] = field(
        default_factory=lambda: [
            "delete",
            "remove",
            "drop",
            "truncate",
            "purge",
            "execute",
            "shell",
            "command",
            "script",
            "payment",
            "transfer",
            "withdraw",
            "refund",
            "export",
            "download",
            "extract",
            "backup",
        ]
    )

    critical_risk_keywords: list[str] = field(
        default_factory=lambda: [
            "admin",
            "root",
            "sudo",
            "elevated",
            "production",
            "prod",
            "live",
            "credentials",
            "secrets",
            "keys",
            "tokens",
        ]
    )

    approval_mode: ApprovalMode = ApprovalMode.ALWAYS
    approval_timeout_seconds: int = 300

    risk_threshold_for_approval: RiskLevel = RiskLevel.HIGH

    auto_escalate_critical: bool = True

    def get_risk_level(self, tool_name: str) -> RiskLevel:
        """Get risk level for a tool."""
        if tool_name in self.critical_risk_tools:
            return RiskLevel.CRITICAL
        if tool_name in self.high_risk_tools:
            return RiskLevel.HIGH
        return RiskLevel.LOW

    def requires_approval(self, tool_name: str, risk_level: RiskLevel) -> bool:
        """Check if approval is required for this tool/risk combination."""
        if not self.enabled:
            return False

        if self.approval_mode == ApprovalMode.NEVER:
            return False

        if self.approval_mode == ApprovalMode.ALWAYS:
            return True

        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        threshold_idx = risk_order.index(self.risk_threshold_for_approval)
        level_idx = risk_order.index(risk_level)

        return level_idx >= threshold_idx

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "high_risk_tools": self.high_risk_tools,
            "critical_risk_tools": self.critical_risk_tools,
            "high_risk_keywords": self.high_risk_keywords,
            "critical_risk_keywords": self.critical_risk_keywords,
            "approval_mode": self.approval_mode.value,
            "approval_timeout_seconds": self.approval_timeout_seconds,
            "risk_threshold_for_approval": self.risk_threshold_for_approval.value,
            "auto_escalate_critical": self.auto_escalate_critical,
        }


@dataclass
class AuditConfig:
    """
    Audit logging configuration.

    Defines what governance events are logged and where.
    """

    enabled: bool = True

    log_permission_checks: bool = True
    log_risk_assessments: bool = True
    log_approvals: bool = True
    log_blocks: bool = True
    log_tool_calls: bool = True
    log_data_access: bool = True

    log_to_file: bool = True
    log_file_path: str | None = None
    log_to_event_bus: bool = True

    retention_days: int = 90
    include_sensitive_params: bool = False

    redact_patterns: list[str] = field(
        default_factory=lambda: [
            r"password",
            r"secret",
            r"token",
            r"api_key",
            r"credential",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "log_permission_checks": self.log_permission_checks,
            "log_risk_assessments": self.log_risk_assessments,
            "log_approvals": self.log_approvals,
            "log_blocks": self.log_blocks,
            "log_tool_calls": self.log_tool_calls,
            "log_data_access": self.log_data_access,
            "log_to_file": self.log_to_file,
            "log_file_path": self.log_file_path,
            "log_to_event_bus": self.log_to_event_bus,
            "retention_days": self.retention_days,
            "include_sensitive_params": self.include_sensitive_params,
            "redact_patterns": self.redact_patterns,
        }


@dataclass
class DataIsolationConfig:
    """
    Data isolation configuration.

    Defines boundaries for session/agent data access.
    """

    enabled: bool = True

    enforce_session_isolation: bool = True
    enforce_agent_isolation: bool = True

    allowed_shared_keys: list[str] = field(default_factory=list)

    blocked_data_patterns: list[str] = field(
        default_factory=lambda: [
            r"\\.env",
            r"credentials",
            r"secrets",
            r"\\.pem",
            r"\\.key",
        ]
    )

    cross_session_access_mode: str = "deny"

    max_data_size_bytes: int = 10 * 1024 * 1024

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "enforce_session_isolation": self.enforce_session_isolation,
            "enforce_agent_isolation": self.enforce_agent_isolation,
            "allowed_shared_keys": self.allowed_shared_keys,
            "blocked_data_patterns": self.blocked_data_patterns,
            "cross_session_access_mode": self.cross_session_access_mode,
            "max_data_size_bytes": self.max_data_size_bytes,
        }


@dataclass
class GuardrailConfig:
    """
    Complete guardrail configuration.

    Combines all governance policies into a single configuration object.
    """

    enabled: bool = True
    name: str = "default"
    description: str = ""

    permission_policy: PermissionPolicy = field(default_factory=PermissionPolicy)
    risk_policy: RiskPolicy = field(default_factory=RiskPolicy)
    audit_config: AuditConfig = field(default_factory=AuditConfig)
    data_isolation: DataIsolationConfig = field(default_factory=DataIsolationConfig)

    fail_closed: bool = True
    block_on_error: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "name": self.name,
            "description": self.description,
            "permission_policy": self.permission_policy.to_dict(),
            "risk_policy": self.risk_policy.to_dict(),
            "audit_config": self.audit_config.to_dict(),
            "data_isolation": self.data_isolation.to_dict(),
            "fail_closed": self.fail_closed,
            "block_on_error": self.block_on_error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuardrailConfig":
        """Create GuardrailConfig from dictionary."""
        perm_data = data.get("permission_policy", {})
        risk_data = data.get("risk_policy", {})
        audit_data = data.get("audit_config", {})
        isolation_data = data.get("data_isolation", {})

        tool_perms = {}
        for name, tp_data in perm_data.get("tool_permissions", {}).items():
            tp_data["risk_level"] = RiskLevel(tp_data.get("risk_level", "low"))
            tool_perms[name] = ToolPermission(**tp_data)

        permission_policy = PermissionPolicy(
            enabled=perm_data.get("enabled", True),
            allowed_tools=perm_data.get("allowed_tools", []),
            blocked_tools=perm_data.get("blocked_tools", []),
            tool_permissions=tool_perms,
            default_allowed=perm_data.get("default_allowed", True),
            default_risk_level=RiskLevel(perm_data.get("default_risk_level", "low")),
            rules=[PermissionRule(**r) for r in perm_data.get("rules", [])],
        )

        risk_policy = RiskPolicy(
            enabled=risk_data.get("enabled", True),
            high_risk_tools=risk_data.get("high_risk_tools", []),
            critical_risk_tools=risk_data.get("critical_risk_tools", []),
            high_risk_keywords=risk_data.get("high_risk_keywords", []),
            critical_risk_keywords=risk_data.get("critical_risk_keywords", []),
            approval_mode=ApprovalMode(risk_data.get("approval_mode", "always")),
            approval_timeout_seconds=risk_data.get("approval_timeout_seconds", 300),
            risk_threshold_for_approval=RiskLevel(
                risk_data.get("risk_threshold_for_approval", "high")
            ),
            auto_escalate_critical=risk_data.get("auto_escalate_critical", True),
        )

        audit_config = AuditConfig(
            enabled=audit_data.get("enabled", True),
            log_permission_checks=audit_data.get("log_permission_checks", True),
            log_risk_assessments=audit_data.get("log_risk_assessments", True),
            log_approvals=audit_data.get("log_approvals", True),
            log_blocks=audit_data.get("log_blocks", True),
            log_tool_calls=audit_data.get("log_tool_calls", True),
            log_data_access=audit_data.get("log_data_access", True),
            log_to_file=audit_data.get("log_to_file", True),
            log_file_path=audit_data.get("log_file_path"),
            log_to_event_bus=audit_data.get("log_to_event_bus", True),
            retention_days=audit_data.get("retention_days", 90),
            include_sensitive_params=audit_data.get("include_sensitive_params", False),
            redact_patterns=audit_data.get("redact_patterns", []),
        )

        data_isolation = DataIsolationConfig(
            enabled=isolation_data.get("enabled", True),
            enforce_session_isolation=isolation_data.get("enforce_session_isolation", True),
            enforce_agent_isolation=isolation_data.get("enforce_agent_isolation", True),
            allowed_shared_keys=isolation_data.get("allowed_shared_keys", []),
            blocked_data_patterns=isolation_data.get("blocked_data_patterns", []),
            cross_session_access_mode=isolation_data.get("cross_session_access_mode", "deny"),
            max_data_size_bytes=isolation_data.get("max_data_size_bytes", 10 * 1024 * 1024),
        )

        return cls(
            enabled=data.get("enabled", True),
            name=data.get("name", "default"),
            description=data.get("description", ""),
            permission_policy=permission_policy,
            risk_policy=risk_policy,
            audit_config=audit_config,
            data_isolation=data_isolation,
            fail_closed=data.get("fail_closed", True),
            block_on_error=data.get("block_on_error", True),
        )

    @classmethod
    def strict(cls) -> "GuardrailConfig":
        """Create a strict configuration for production environments."""
        return cls(
            enabled=True,
            name="strict",
            description="Strict governance for production environments",
            permission_policy=PermissionPolicy(
                enabled=True,
                default_allowed=False,
            ),
            risk_policy=RiskPolicy(
                enabled=True,
                approval_mode=ApprovalMode.ALWAYS,
                risk_threshold_for_approval=RiskLevel.MEDIUM,
                auto_escalate_critical=True,
            ),
            audit_config=AuditConfig(
                enabled=True,
                log_permission_checks=True,
                log_risk_assessments=True,
                log_approvals=True,
                log_blocks=True,
                log_tool_calls=True,
                log_data_access=True,
            ),
            data_isolation=DataIsolationConfig(
                enabled=True,
                enforce_session_isolation=True,
                enforce_agent_isolation=True,
            ),
            fail_closed=True,
            block_on_error=True,
        )

    @classmethod
    def permissive(cls) -> "GuardrailConfig":
        """Create a permissive configuration for development environments."""
        return cls(
            enabled=True,
            name="permissive",
            description="Permissive governance for development",
            permission_policy=PermissionPolicy(
                enabled=True,
                default_allowed=True,
            ),
            risk_policy=RiskPolicy(
                enabled=True,
                approval_mode=ApprovalMode.NEVER,
            ),
            audit_config=AuditConfig(
                enabled=True,
                log_blocks=True,
                log_tool_calls=True,
            ),
            data_isolation=DataIsolationConfig(
                enabled=False,
            ),
            fail_closed=False,
            block_on_error=False,
        )
