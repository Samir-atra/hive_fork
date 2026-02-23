"""
Risk Classification for Tool Actions

Provides risk assessment for tool calls based on:
- Tool name patterns
- Parameter values
- Keywords in tool names or inputs
- Custom risk rules
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from framework.governance.config import RiskLevel, RiskPolicy

logger = logging.getLogger(__name__)


@dataclass
class RiskContext:
    """Context for risk assessment."""

    tool_name: str
    tool_input: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    agent_id: str | None = None
    node_id: str | None = None
    execution_id: str | None = None
    user_id: str | None = None
    environment: str = "development"
    previous_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "node_id": self.node_id,
            "execution_id": self.execution_id,
            "user_id": self.user_id,
            "environment": self.environment,
            "previous_calls_count": len(self.previous_calls),
        }


@dataclass
class RiskAssessment:
    """Result of risk assessment."""

    risk_level: RiskLevel
    tool_name: str
    reasons: list[str]
    confidence: float = 1.0
    requires_approval: bool = False
    escalation_recommended: bool = False
    context: RiskContext | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    mitigations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "tool_name": self.tool_name,
            "reasons": self.reasons,
            "confidence": self.confidence,
            "requires_approval": self.requires_approval,
            "escalation_recommended": self.escalation_recommended,
            "context": self.context.to_dict() if self.context else None,
            "timestamp": self.timestamp.isoformat(),
            "mitigations": self.mitigations,
        }


class RiskClassifier:
    """
    Classifies risk level of tool actions.

    Features:
    - Tool name-based risk classification
    - Keyword-based risk detection
    - Parameter analysis for risk factors
    - Environment-aware risk assessment
    - Custom risk rule evaluation
    """

    HIGH_RISK_PATTERNS = [
        r".*delete.*",
        r".*remove.*",
        r".*drop.*",
        r".*truncate.*",
        r".*purge.*",
        r".*execute.*",
        r".*shell.*",
        r".*command.*",
        r".*payment.*",
        r".*transfer.*",
        r".*withdraw.*",
        r".*refund.*",
        r".*export.*",
        r".*backup.*",
        r".*admin.*",
    ]

    CRITICAL_RISK_PATTERNS = [
        r".*production.*",
        r".*prod.*",
        r".*live.*",
        r".*credential.*",
        r".*secret.*",
        r".*token.*",
        r".*api[_-]?key.*",
        r".*root.*",
        r".*sudo.*",
        r".*elevated.*",
    ]

    SENSITIVE_PARAM_PATTERNS = [
        r"password",
        r"secret",
        r"token",
        r"api_key",
        r"credential",
        r"private",
        r"ssh_key",
    ]

    def __init__(self, policy: RiskPolicy):
        self.policy = policy
        self._compiled_high_risk = self._compile_patterns(self.HIGH_RISK_PATTERNS)
        self._compiled_critical_risk = self._compile_patterns(self.CRITICAL_RISK_PATTERNS)
        self._compiled_sensitive = self._compile_patterns(self.SENSITIVE_PARAM_PATTERNS)

    def _compile_patterns(self, patterns: list[str]) -> list[re.Pattern]:
        """Compile regex patterns."""
        return [re.compile(p, re.IGNORECASE) for p in patterns]

    def assess_risk(
        self,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        context: RiskContext | None = None,
    ) -> RiskAssessment:
        """
        Assess the risk level of a tool call.

        Args:
            tool_name: Name of the tool
            tool_input: Input parameters for the tool
            context: Additional context for risk assessment

        Returns:
            RiskAssessment with risk level and reasoning
        """
        if not self.policy.enabled:
            return RiskAssessment(
                risk_level=RiskLevel.LOW,
                tool_name=tool_name,
                reasons=["Risk policy is disabled"],
                context=context,
            )

        if context is None:
            context = RiskContext(tool_name=tool_name)

        if tool_input:
            context.tool_input = tool_input

        reasons: list[str] = []
        risk_score = 0.0
        mitigations: list[str] = []

        policy_risk = self.policy.get_risk_level(tool_name)
        if policy_risk == RiskLevel.CRITICAL:
            risk_score += 100
            reasons.append(f"Tool '{tool_name}' is marked as critical risk in policy")
        elif policy_risk == RiskLevel.HIGH:
            risk_score += 50
            reasons.append(f"Tool '{tool_name}' is marked as high risk in policy")

        tool_risk = self._assess_tool_name_risk(tool_name)
        if tool_risk["risk_level"] == RiskLevel.CRITICAL:
            risk_score += 80
            reasons.extend(tool_risk["reasons"])
        elif tool_risk["risk_level"] == RiskLevel.HIGH:
            risk_score += 40
            reasons.extend(tool_risk["reasons"])
        elif tool_risk["risk_level"] == RiskLevel.MEDIUM:
            risk_score += 20
            reasons.extend(tool_risk["reasons"])

        if tool_input:
            param_risk = self._assess_parameter_risk(tool_input)
            risk_score += param_risk["score"]
            reasons.extend(param_risk["reasons"])
            mitigations.extend(param_risk.get("mitigations", []))

        env_risk = self._assess_environment_risk(context)
        risk_score += env_risk["score"]
        reasons.extend(env_risk["reasons"])

        call_pattern_risk = self._assess_call_pattern_risk(context)
        risk_score += call_pattern_risk["score"]
        reasons.extend(call_pattern_risk["reasons"])

        final_risk_level = self._score_to_risk_level(risk_score)

        requires_approval = self.policy.requires_approval(tool_name, final_risk_level)

        escalation_recommended = (
            final_risk_level == RiskLevel.CRITICAL and self.policy.auto_escalate_critical
        )

        return RiskAssessment(
            risk_level=final_risk_level,
            tool_name=tool_name,
            reasons=reasons,
            confidence=min(1.0, len(reasons) / 3.0) if reasons else 0.5,
            requires_approval=requires_approval,
            escalation_recommended=escalation_recommended,
            context=context,
            mitigations=mitigations,
        )

    def _assess_tool_name_risk(self, tool_name: str) -> dict[str, Any]:
        """Assess risk based on tool name patterns."""
        reasons: list[str] = []
        risk_level = RiskLevel.LOW

        for pattern in self._compiled_critical_risk:
            if pattern.search(tool_name):
                risk_level = RiskLevel.CRITICAL
                reasons.append(f"Tool name matches critical risk pattern: {pattern.pattern}")
                break

        if risk_level != RiskLevel.CRITICAL:
            for pattern in self._compiled_high_risk:
                if pattern.search(tool_name):
                    risk_level = RiskLevel.HIGH
                    reasons.append(f"Tool name matches high risk pattern: {pattern.pattern}")
                    break

        for keyword in self.policy.critical_risk_keywords:
            if keyword.lower() in tool_name.lower():
                risk_level = RiskLevel.CRITICAL
                reasons.append(f"Tool name contains critical keyword: {keyword}")

        for keyword in self.policy.high_risk_keywords:
            if keyword.lower() in tool_name.lower():
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.HIGH
                reasons.append(f"Tool name contains high risk keyword: {keyword}")

        return {
            "risk_level": risk_level,
            "reasons": reasons,
        }

    def _assess_parameter_risk(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Assess risk based on parameter values."""
        reasons: list[str] = []
        mitigations: list[str] = []
        score = 0.0

        for param_name, param_value in tool_input.items():
            for pattern in self._compiled_sensitive:
                if pattern.search(param_name):
                    score += 30
                    reasons.append(f"Parameter '{param_name}' appears to be sensitive")
                    mitigations.append(f"Consider redacting or encrypting '{param_name}'")

            if isinstance(param_value, str):
                if any(kw in param_value.lower() for kw in ["delete", "drop", "truncate"]):
                    score += 25
                    reasons.append(f"Parameter '{param_name}' contains destructive keyword")

                if "production" in param_value.lower() or "prod" in param_value.lower():
                    score += 35
                    reasons.append(f"Parameter '{param_name}' references production environment")

        return {
            "score": score,
            "reasons": reasons,
            "mitigations": mitigations,
        }

    def _assess_environment_risk(self, context: RiskContext) -> dict[str, Any]:
        """Assess risk based on execution environment."""
        reasons: list[str] = []
        score = 0.0

        if context.environment == "production":
            score += 30
            reasons.append("Executing in production environment")
        elif context.environment == "staging":
            score += 15
            reasons.append("Executing in staging environment")

        return {
            "score": score,
            "reasons": reasons,
        }

    def _assess_call_pattern_risk(self, context: RiskContext) -> dict[str, Any]:
        """Assess risk based on call patterns."""
        reasons: list[str] = []
        score = 0.0

        recent_calls = context.previous_calls[-10:]

        if len(recent_calls) >= 5:
            tool_counts: dict[str, int] = {}
            for call in recent_calls:
                tool_name = call.get("tool_name", "")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            for tool_name, count in tool_counts.items():
                if count >= 3:
                    score += 10
                    reasons.append(f"Repeated calls to '{tool_name}' ({count} times)")

        return {
            "score": score,
            "reasons": reasons,
        }

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= 100:
            return RiskLevel.CRITICAL
        elif score >= 50:
            return RiskLevel.HIGH
        elif score >= 20:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def get_risk_summary(self, assessments: list[RiskAssessment]) -> dict[str, Any]:
        """Generate a summary of risk assessments."""
        if not assessments:
            return {"total": 0, "by_level": {}, "approval_required": 0}

        by_level: dict[str, int] = {}
        for level in RiskLevel:
            by_level[level.value] = 0

        approval_count = 0
        escalation_count = 0

        for assessment in assessments:
            by_level[assessment.risk_level.value] += 1
            if assessment.requires_approval:
                approval_count += 1
            if assessment.escalation_recommended:
                escalation_count += 1

        return {
            "total": len(assessments),
            "by_level": by_level,
            "approval_required": approval_count,
            "escalation_recommended": escalation_count,
        }
