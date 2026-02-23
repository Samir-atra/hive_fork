# Trust & Governance Layer

A first-class architectural layer for enterprise-grade trust, auditability, and control over autonomous agents.

## Overview

The Governance Layer provides deterministic guardrails for autonomous agents, enabling:

- **Deterministic Permissions**: Tool-level access controls with allowlists/blocklists
- **Risk-Based Approvals**: Human approval workflows for high-impact actions
- **Full Auditability**: Comprehensive logging of all governance decisions
- **Data Isolation**: Per-session/agent data boundaries

## Quick Start

```python
from framework.governance import GuardrailConfig, GuardrailEngine

# Create a strict configuration for production
config = GuardrailConfig.strict()

# Initialize the guardrail engine
guardrail = GuardrailEngine(config, event_bus)
await guardrail.initialize()

# Evaluate a tool call
result = await guardrail.evaluate_tool_call(tool_use)

if result.blocked:
    return ToolResult(
        tool_use_id=tool_use.id,
        content={"error": f"Blocked: {result.reason}"},
        is_error=True
    )

if result.requires_approval:
    approved = await guardrail.request_approval(result.approval_request)
    if not approved:
        return ToolResult(
            tool_use_id=tool_use.id,
            content={"error": "Tool call was not approved"},
            is_error=True
        )

# Proceed with tool execution
```

## Configuration

### GuardrailConfig

The main configuration object that combines all governance policies:

```python
from framework.governance import GuardrailConfig, PermissionPolicy, RiskPolicy

config = GuardrailConfig(
    enabled=True,
    name="production",
    permission_policy=PermissionPolicy(
        allowed_tools=["web_search", "email_send"],
        blocked_tools=["file_delete", "shell_execute"],
        default_allowed=False,
    ),
    risk_policy=RiskPolicy(
        high_risk_tools=["payment_process", "data_export"],
        approval_mode=ApprovalMode.ALWAYS,
    ),
)
```

### Preset Configurations

```python
# Strict - for production environments
config = GuardrailConfig.strict()

# Permissive - for development environments
config = GuardrailConfig.permissive()
```

## Permission Policy

Control which tools agents can use:

```python
from framework.governance import PermissionPolicy, ToolPermission

policy = PermissionPolicy(
    # Only allow specific tools
    allowed_tools=["web_search", "email_send"],
    
    # Block dangerous tools
    blocked_tools=["file_delete", "shell_execute"],
    
    # Per-tool configurations
    tool_permissions={
        "api_call": ToolPermission(
            tool_name="api_call",
            allowed=True,
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            allowed_parameters={"method": ["GET", "POST"]},
            rate_limit_per_minute=10,
        )
    },
    
    # Default behavior for unlisted tools
    default_allowed=False,
)
```

### Features

- **Allowlist/Blocklist**: Simple allow/deny lists for tool access
- **Parameter Restrictions**: Limit which parameter values are allowed
- **Rate Limiting**: Control how frequently tools can be called
- **Custom Rules**: Define complex permission rules

## Risk Classification

Automatically assess risk levels for tool actions:

```python
from framework.governance import RiskClassifier, RiskPolicy, RiskContext

policy = RiskPolicy(
    high_risk_tools=["payment_process", "data_export"],
    critical_risk_tools=["admin_access", "delete_all"],
    approval_mode=ApprovalMode.THRESHOLD,
    risk_threshold_for_approval=RiskLevel.HIGH,
)

classifier = RiskClassifier(policy)

context = RiskContext(
    tool_name="payment_process",
    environment="production",
)

assessment = classifier.assess_risk("payment_process", {"amount": 1000}, context)

print(f"Risk Level: {assessment.risk_level}")
print(f"Requires Approval: {assessment.requires_approval}")
print(f"Reasons: {assessment.reasons}")
```

### Risk Levels

- **LOW**: Safe operations, no restrictions
- **MEDIUM**: Moderate risk, may require approval based on policy
- **HIGH**: Significant risk, typically requires approval
- **CRITICAL**: Maximum risk, always requires approval and may escalate

## Audit Logging

Comprehensive audit trail for compliance and debugging:

```python
from framework.governance import AuditConfig, AuditLogger, AuditEvent

config = AuditConfig(
    enabled=True,
    log_permission_checks=True,
    log_risk_assessments=True,
    log_approvals=True,
    log_blocks=True,
    log_tool_calls=True,
    log_to_file=True,
    log_file_path="/var/log/hive/governance.jsonl",
    retention_days=90,
)

logger = AuditLogger(config, event_bus)

# Log events
await logger.log_event(AuditEvent(
    event_type=AuditEventType.TOOL_BLOCKED,
    tool_name="dangerous_tool",
    reason="Tool not in allowlist",
))

# Query events
events = logger.get_events(
    event_type=AuditEventType.TOOL_BLOCKED,
    start_time=datetime.now() - timedelta(days=1),
)

# Get statistics
stats = logger.get_statistics()
```

### Sensitive Data Redaction

The audit logger automatically redacts sensitive parameters:

```python
config = AuditConfig(
    redact_patterns=[
        r"password",
        r"secret",
        r"token",
        r"api_key",
    ],
)
```

## Data Isolation

Enforce boundaries between sessions and agents:

```python
from framework.governance import DataIsolationConfig

config = DataIsolationConfig(
    enabled=True,
    enforce_session_isolation=True,
    enforce_agent_isolation=True,
    blocked_data_patterns=[r"\.env", r"credentials", r"\.pem"],
    cross_session_access_mode="deny",
)
```

## Guardrail Engine

The central orchestration component:

```python
from framework.governance import GuardrailEngine

engine = GuardrailEngine(config, event_bus)
await engine.initialize()

# Evaluate tool calls
result = await engine.evaluate_tool_call(tool_use, context={
    "session_id": "session_123",
    "agent_id": "agent_456",
    "environment": "production",
})

# Check data access
allowed, reason = await engine.check_data_access(
    key="/data/sensitive.json",
    operation="read",
    context={"session_id": "session_123"},
)

# Get statistics
stats = engine.get_statistics()
```

### Approval Callbacks

Implement custom approval workflows:

```python
from framework.governance.engine import ApprovalCallback, ApprovalRequest

class MyApprovalCallback(ApprovalCallback):
    async def request_approval(self, request: ApprovalRequest) -> bool:
        # Send notification to approval system
        # Wait for human response
        # Return approval decision
        return await self.wait_for_human_response(request)

engine.set_approval_callback(MyApprovalCallback())
```

## Wrapped Executor

Integrate guardrails with existing tool executors:

```python
from framework.governance.engine import create_wrapped_executor

original_executor = tool_registry.get_executor()
wrapped_executor = create_wrapped_executor(original_executor, guardrail)

# Use the wrapped executor - guardrails are automatically enforced
tool_registry._tools["my_tool"] = RegisteredTool(tool, wrapped_executor)
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GuardrailEngine                     │
│  ┌─────────────────────────────────────────────┐   │
│  │              evaluate_tool_call              │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │          PermissionEvaluator                 │   │
│  │   - Tool allowlist/blocklist                 │   │
│  │   - Parameter restrictions                   │   │
│  │   - Rate limiting                            │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │            RiskClassifier                    │   │
│  │   - Tool name patterns                       │   │
│  │   - Keyword detection                        │   │
│  │   - Parameter analysis                       │   │
│  │   - Environment awareness                    │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │         ApprovalWorkflow                     │   │
│  │   - Human-in-the-loop                        │   │
│  │   - Timeout handling                         │   │
│  │   - Escalation                               │   │
│  └─────────────────┬───────────────────────────┘   │
│                    │                                │
│  ┌─────────────────▼───────────────────────────┐   │
│  │            AuditLogger                       │   │
│  │   - Event logging                            │   │
│  │   - Sensitive data redaction                 │   │
│  │   - Statistics & querying                    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Event Types

The governance layer emits events to the EventBus:

| Event Type | Description |
|------------|-------------|
| `permission_check` | Permission evaluation |
| `permission_granted` | Tool access allowed |
| `permission_denied` | Tool access denied |
| `risk_assessment` | Risk level determined |
| `approval_requested` | Human approval needed |
| `approval_granted` | Approval given |
| `approval_denied` | Approval rejected |
| `tool_blocked` | Tool execution blocked |
| `tool_executed` | Tool execution completed |
| `data_isolation_violation` | Data boundary violation |

## Best Practices

1. **Use Strict Configuration for Production**
   ```python
   config = GuardrailConfig.strict()
   ```

2. **Define Clear Risk Thresholds**
   ```python
   risk_policy = RiskPolicy(
       risk_threshold_for_approval=RiskLevel.HIGH,
       auto_escalate_critical=True,
   )
   ```

3. **Enable Comprehensive Audit Logging**
   ```python
   audit_config = AuditConfig(
       log_permission_checks=True,
       log_risk_assessments=True,
       log_approvals=True,
       log_blocks=True,
   )
   ```

4. **Implement Proper Approval Callbacks**
   - Handle timeouts gracefully
   - Provide clear context to approvers
   - Log all decisions

5. **Test Governance Policies**
   - Verify blocked tools are properly blocked
   - Test approval workflows
   - Validate audit logs

## Related Issues

- #3623: Operational Trust for Production AI Agents
- #3930: Core Evaluation System
- #5133: Add Compliance Audit Logging for Agent Workflows

## License

Apache License 2.0
