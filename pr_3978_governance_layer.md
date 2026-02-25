# Trust & Governance as a First-Class Layer for Autonomous Agents

Resolves #3978

## Summary

Implements a dedicated Guardrail Layer as a first-class architectural component for enterprise-grade autonomous agent governance. This provides deterministic permissions, risk-based approvals, full auditability, and strict data isolation - making autonomous behavior meaningfully trustable in production environments.

## Changes

### Core Components

- **`core/framework/governance/__init__.py`** - Module exports and documentation
- **`core/framework/governance/config.py`** - Configuration models:
  - `GuardrailConfig` - Main configuration combining all policies
  - `PermissionPolicy` - Tool allowlist/blocklist configuration
  - `RiskPolicy` - Risk classification and approval requirements
  - `AuditConfig` - Audit logging configuration
  - `DataIsolationConfig` - Data boundary enforcement
  - `ToolPermission` - Per-tool permission settings
  - `RiskLevel` enum - LOW, MEDIUM, HIGH, CRITICAL
  - `ApprovalMode` enum - NEVER, ALWAYS, FIRST_TIME, THRESHOLD

- **`core/framework/governance/permissions.py`** - Permission evaluation:
  - `PermissionEvaluator` - Evaluates tool access permissions
  - `PermissionCheckResult` - Permission check outcome
  - Supports allowlists, blocklists, parameter restrictions, rate limiting

- **`core/framework/governance/risk.py`** - Risk classification:
  - `RiskClassifier` - Assesses risk level of tool actions
  - `RiskContext` - Context for risk assessment
  - `RiskAssessment` - Risk evaluation result
  - Pattern-based keyword detection
  - Environment-aware risk assessment

- **`core/framework/governance/audit.py`** - Audit logging:
  - `AuditLogger` - Comprehensive audit trail logging
  - `AuditEvent` - Audit event record
  - `AuditEventType` enum - All governance event types
  - Sensitive data redaction
  - File and EventBus logging support

- **`core/framework/governance/engine.py`** - Orchestration:
  - `GuardrailEngine` - Central governance orchestration
  - `GuardrailResult` - Evaluation result
  - `ApprovalRequest` - Human approval request
  - `ApprovalCallback` - Interface for approval workflows
  - `create_wrapped_executor()` - Integration with ToolRegistry

### Tests

- **`core/tests/test_governance.py`** - Comprehensive unit tests:
  - Configuration tests (default, strict, permissive, serialization)
  - Permission policy tests (allowlist, blocklist, overrides, rate limits)
  - Risk classifier tests (levels, keywords, parameters, environment)
  - Audit logger tests (logging, redaction, statistics)
  - Engine tests (evaluation, approval, data isolation)
  - Wrapped executor tests

### Documentation

- **`core/framework/governance/README.md`** - Complete usage guide with:
  - Quick start examples
  - Configuration reference
  - Architecture diagram
  - Best practices
  - Event types reference

## Features

### 1. Deterministic Permissions
- Tool allowlists and blocklists
- Per-tool permission configurations
- Parameter-level restrictions
- Rate limiting per tool
- Custom permission rules

### 2. Risk-Based Approvals
- Automatic risk classification (LOW, MEDIUM, HIGH, CRITICAL)
- Pattern-based risk detection
- Parameter analysis for risk factors
- Environment-aware assessment
- Configurable approval thresholds

### 3. Full Auditability
- Comprehensive event logging
- Sensitive data redaction
- Event Bus integration
- Query capabilities
- Statistics and reporting

### 4. Data Isolation
- Session-level isolation
- Agent-level isolation
- Blocked data patterns
- Cross-session access control

## Usage Example

```python
from framework.governance import GuardrailConfig, GuardrailEngine

# Create strict configuration for production
config = GuardrailConfig.strict()

# Initialize engine
engine = GuardrailEngine(config, event_bus)
await engine.initialize()

# Evaluate tool calls
result = await engine.evaluate_tool_call(tool_use)

if result.blocked:
    return error_response(f"Blocked: {result.reason}")

if result.requires_approval:
    approved = await engine.request_approval(result.approval_request)
    if not approved:
        return error_response("Not approved")

# Execute the tool
return await execute_tool(tool_use)
```

## Configuration Presets

```python
# Strict - for production
config = GuardrailConfig.strict()

# Permissive - for development  
config = GuardrailConfig.permissive()

# Custom
config = GuardrailConfig(
    permission_policy=PermissionPolicy(
        allowed_tools=["web_search", "email_send"],
        default_allowed=False,
    ),
    risk_policy=RiskPolicy(
        approval_mode=ApprovalMode.THRESHOLD,
        risk_threshold_for_approval=RiskLevel.HIGH,
    ),
)
```

## Testing

Run the governance tests:

```bash
cd core
uv run pytest tests/test_governance.py -v
```

## Related Issues

- #3623: Operational Trust for Production AI Agents
- #3671: Enterprise readiness gaps for self-evolving agents
- #3930: Core Evaluation System
- #5133: Add Compliance Audit Logging for Agent Workflows

## Checklist

- [x] Code follows project conventions
- [x] Unit tests added
- [x] Documentation updated
- [x] All governance components implemented
- [x] Integration with existing framework patterns (EventBus, HITL)
