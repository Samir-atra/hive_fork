"""
Permission Policy Implementation

Provides deterministic permission evaluation for tool access control.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from framework.governance.config import PermissionPolicy, PermissionRule, ToolPermission

logger = logging.getLogger(__name__)


@dataclass
class PermissionCheckResult:
    """Result of a permission check."""

    allowed: bool
    tool_name: str
    reason: str
    permission: ToolPermission | None = None
    rule_matched: PermissionRule | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tool_name": self.tool_name,
            "reason": self.reason,
            "permission": self.permission.to_dict() if self.permission else None,
            "rule_matched": self.rule_matched.to_dict() if self.rule_matched else None,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class PermissionEvaluator:
    """
    Evaluates permissions for tool access.

    Features:
    - Tool allowlist/blocklist evaluation
    - Per-tool permission configuration
    - Parameter-level restrictions
    - Rule-based evaluation
    - Rate limiting tracking
    """

    def __init__(self, policy: PermissionPolicy):
        self.policy = policy
        self._rate_limit_counters: dict[str, list[datetime]] = {}
        self._first_use_tracker: set[str] = set()

    def check_permission(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> PermissionCheckResult:
        """
        Check if a tool call is permitted.

        Args:
            tool_name: Name of the tool to check
            tool_input: Input parameters for the tool
            context: Additional context for evaluation

        Returns:
            PermissionCheckResult with allowed status and reasoning
        """
        if not self.policy.enabled:
            return PermissionCheckResult(
                allowed=True,
                tool_name=tool_name,
                reason="Permission policy is disabled",
                context=context or {},
            )

        permission = self.policy.get_tool_permission(tool_name)

        if not permission.allowed:
            return PermissionCheckResult(
                allowed=False,
                tool_name=tool_name,
                reason=f"Tool '{tool_name}' is not allowed by policy",
                permission=permission,
                context=context or {},
            )

        if tool_input:
            param_result = self._check_parameter_restrictions(tool_name, tool_input, permission)
            if not param_result.allowed:
                return param_result

        rule_result = self._check_rules(tool_name, tool_input, context)
        if rule_result:
            return rule_result

        rate_result = self._check_rate_limit(tool_name, permission)
        if not rate_result.allowed:
            return rate_result

        return PermissionCheckResult(
            allowed=True,
            tool_name=tool_name,
            reason="Tool is allowed by policy",
            permission=permission,
            context=context or {},
        )

    def _check_parameter_restrictions(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        permission: ToolPermission,
    ) -> PermissionCheckResult:
        """Check parameter-level restrictions."""
        if permission.allowed_parameters:
            for param_name, allowed_values in permission.allowed_parameters.items():
                if param_name in tool_input:
                    actual_value = tool_input[param_name]
                    if isinstance(allowed_values, list):
                        if actual_value not in allowed_values:
                            return PermissionCheckResult(
                                allowed=False,
                                tool_name=tool_name,
                                reason=f"Parameter '{param_name}' value '{actual_value}' is not in allowed list",
                                permission=permission,
                            )
                    elif actual_value != allowed_values:
                        return PermissionCheckResult(
                            allowed=False,
                            tool_name=tool_name,
                            reason=f"Parameter '{param_name}' has invalid value",
                            permission=permission,
                        )

        if permission.blocked_parameter_values:
            for param_name, blocked_values in permission.blocked_parameter_values.items():
                if param_name in tool_input:
                    actual_value = tool_input[param_name]
                    if actual_value in blocked_values:
                        return PermissionCheckResult(
                            allowed=False,
                            tool_name=tool_name,
                            reason=f"Parameter '{param_name}' value '{actual_value}' is blocked",
                            permission=permission,
                        )

        return PermissionCheckResult(
            allowed=True,
            tool_name=tool_name,
            reason="Parameters are allowed",
            permission=permission,
        )

    def _check_rules(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> PermissionCheckResult | None:
        """Check custom rules in priority order."""
        sorted_rules = sorted(self.policy.rules, key=lambda r: r.priority)

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            try:
                if self._evaluate_rule_condition(rule, tool_name, tool_input, context):
                    allowed = rule.action.lower() in ("allow", "permit", "grant")
                    return PermissionCheckResult(
                        allowed=allowed,
                        tool_name=tool_name,
                        reason=f"Rule '{rule.name}' matched: {rule.action}",
                        rule_matched=rule,
                        context=context or {},
                    )
            except Exception as e:
                logger.warning(f"Error evaluating rule '{rule.name}': {e}")

        return None

    def _evaluate_rule_condition(
        self,
        rule: PermissionRule,
        tool_name: str,
        tool_input: dict[str, Any] | None,
        context: dict[str, Any] | None,
    ) -> bool:
        """Evaluate a rule condition."""
        condition = rule.condition.lower()

        if "tool_name" in condition:
            if (
                f"tool_name == '{tool_name}'" in condition
                or f'tool_name == "{tool_name}"' in condition
            ):
                return True
            if f"tool_name in" in condition:
                match = re.search(r"tool_name in \[([^\]]+)\]", condition)
                if match:
                    tools_str = match.group(1)
                    tools = [t.strip().strip("'\"") for t in tools_str.split(",")]
                    if tool_name in tools:
                        return True

        if "input" in condition and tool_input:
            for key, value in tool_input.items():
                if f"input['{key}']" in condition or f'input["{key}"]' in condition:
                    if str(value).lower() in condition:
                        return True

        if "context" in condition and context:
            for key, value in context.items():
                if f"context['{key}']" in condition or f'context["{key}"]' in condition:
                    if str(value).lower() in condition:
                        return True

        return False

    def _check_rate_limit(
        self,
        tool_name: str,
        permission: ToolPermission,
    ) -> PermissionCheckResult:
        """Check rate limiting for a tool."""
        if permission.rate_limit_per_minute is None:
            return PermissionCheckResult(
                allowed=True,
                tool_name=tool_name,
                reason="No rate limit configured",
                permission=permission,
            )

        now = datetime.now()
        minute_ago = now.timestamp() - 60

        if tool_name not in self._rate_limit_counters:
            self._rate_limit_counters[tool_name] = []

        self._rate_limit_counters[tool_name] = [
            ts for ts in self._rate_limit_counters[tool_name] if ts.timestamp() > minute_ago
        ]

        calls_in_minute = len(self._rate_limit_counters[tool_name])

        if calls_in_minute >= permission.rate_limit_per_minute:
            return PermissionCheckResult(
                allowed=False,
                tool_name=tool_name,
                reason=f"Rate limit exceeded ({calls_in_minute}/{permission.rate_limit_per_minute} calls per minute)",
                permission=permission,
            )

        self._rate_limit_counters[tool_name].append(now)

        return PermissionCheckResult(
            allowed=True,
            tool_name=tool_name,
            reason="Within rate limit",
            permission=permission,
        )

    def is_first_use(self, tool_name: str) -> bool:
        """Check if this is the first use of a tool (for first_time approval mode)."""
        if tool_name in self._first_use_tracker:
            return False
        self._first_use_tracker.add(tool_name)
        return True

    def reset_rate_limits(self, tool_name: str | None = None) -> None:
        """Reset rate limit counters."""
        if tool_name:
            self._rate_limit_counters.pop(tool_name, None)
        else:
            self._rate_limit_counters.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get permission evaluator statistics."""
        return {
            "tools_with_rate_limits": len(self._rate_limit_counters),
            "tools_used": len(self._first_use_tracker),
            "rules_count": len(self.policy.rules),
        }
