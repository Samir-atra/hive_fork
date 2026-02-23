# Business Workflow Mapping

Map AI agents to real business workflows — onboarding, CRM, customer
support, operations, and more — so every team can see which agents
drive which processes and track performance end-to-end.

> **Status:** Foundation layer (Phase 1).  Agent tagging, workflow
> definitions, a programmatic registry, and a dashboard summary API
> are available now.  Visual dashboard and enterprise integrations
> are planned for later phases.

---

## Quick Start

```python
from framework.workflows import (
    WorkflowRegistry,
    WorkflowCategory,
    WorkflowStep,
    AgentRole,
)

# 1. Create a registry (persists to ~/.hive/workflows/)
registry = WorkflowRegistry()

# 2. Define a business workflow
registry.create_workflow(
    id="customer-support-flow",
    name="Customer Support",
    category=WorkflowCategory.CUSTOMER_SUPPORT,
    description="End-to-end customer ticket resolution",
    owner_team="cs",
    steps=[
        WorkflowStep(id="triage", name="Ticket Triage", order=1),
        WorkflowStep(id="resolve", name="Resolution", order=2),
        WorkflowStep(id="followup", name="Follow-Up", order=3),
    ],
)

# 3. Map agents to the workflow
registry.map_agent(
    agent_id="support-ticket-agent",
    agent_name="Support Ticket Agent",
    workflow_ids=["customer-support-flow"],
    role=AgentRole.PRIMARY,
    tags=["tier-1", "emea"],
    team="cs",
)

# 4. Generate a dashboard summary
summary = registry.generate_dashboard_summary(
    all_agent_ids=["support-ticket-agent", "sales-agent", "onboarding-agent"],
)
print(f"Workflows: {summary.total_workflows}")
print(f"Mapped agents: {summary.total_agents}")
print(f"Unmapped agents: {summary.unmapped_agents}")
```

---

## Core Concepts

### Workflow Definition

A `WorkflowDefinition` describes a repeatable business process composed
of ordered steps:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Human-readable name |
| `category` | `WorkflowCategory` | Business function (see below) |
| `description` | `str` | What the workflow accomplishes |
| `owner_team` | `str` | Responsible team |
| `steps` | `list[WorkflowStep]` | Ordered steps |
| `status` | `WorkflowStatus` | `draft`, `active`, `paused`, `archived` |
| `tags` | `list[str]` | Free-form labels |

**Built-in categories** (`WorkflowCategory`):

| Category | Value |
|----------|-------|
| Onboarding | `onboarding` |
| CRM | `crm` |
| Customer Support | `customer_support` |
| Operations | `operations` |
| Sales | `sales` |
| Marketing | `marketing` |
| Finance | `finance` |
| HR | `hr` |
| Engineering | `engineering` |
| Custom | `custom` |

### Workflow Steps

Each step in a workflow can reference one or more agents:

```python
WorkflowStep(
    id="triage",
    name="Ticket Triage",
    description="Categorize and prioritize incoming tickets",
    order=1,
    agent_ids=["triage-agent"],
    required=True,
)
```

### Agent-to-Workflow Mapping

An `AgentWorkflowMapping` links an agent to one or more workflows
with a role and metadata:

```python
registry.map_agent(
    agent_id="support-agent",
    workflow_ids=["customer-support-flow", "escalation-flow"],
    role=AgentRole.PRIMARY,       # or SUPPORTING, FALLBACK, MONITOR
    tags=["tier-1", "24x7"],
    team="cs",
)
```

| Role | Description |
|------|-------------|
| `PRIMARY` | Main handler for the workflow step |
| `SUPPORTING` | Assists the primary agent |
| `FALLBACK` | Activates when the primary fails |
| `MONITOR` | Observes and alerts without acting |

---

## Registry API

### Workflow CRUD

```python
registry = WorkflowRegistry()

# Create
wf = registry.create_workflow(id="...", name="...", category=...)

# Read
wf = registry.get_workflow("workflow-id")

# List (with optional filters)
all_wfs = registry.list_workflows()
crm_wfs = registry.list_workflows(category=WorkflowCategory.CRM)
active_wfs = registry.list_workflows(status=WorkflowStatus.ACTIVE)
tagged_wfs = registry.list_workflows(tag="important")

# Update
registry.update_workflow("workflow-id", name="New Name", status=WorkflowStatus.ACTIVE)

# Delete (also cleans agent mappings)
registry.delete_workflow("workflow-id")
```

### Agent Mapping

```python
# Map (creates or merges)
registry.map_agent(agent_id="a1", workflow_ids=["wf-1", "wf-2"])

# Query
mapping = registry.get_agent_mapping("a1")
agents = registry.get_agents_for_workflow("wf-1")
unmapped = registry.get_unmapped_agents(["a1", "a2", "a3"])

# Unmap
registry.unmap_agent("a1", "wf-1")
```

### Dashboard Summary

```python
summary = registry.generate_dashboard_summary(
    all_agent_ids=["a1", "a2", "a3"],
    performance_data={
        "a1": {
            "wf-1": {
                "total_runs": 100,
                "successful_runs": 95,
                "failed_runs": 5,
                "avg_latency_ms": 250.0,
                "total_tokens": 50000,
            }
        }
    },
)
```

The returned `WorkflowDashboardSummary` contains:
- Total workflows and mapped agents
- Workflows grouped by category and status
- List of unmapped agents
- Per-workflow summaries with per-agent performance snapshots

---

## Persistence

All data is stored as JSON in `~/.hive/workflows/`:

```
~/.hive/workflows/
├── workflows.json   # Workflow definitions
└── mappings.json    # Agent-to-workflow mappings
```

You can point to a custom directory:

```python
registry = WorkflowRegistry(storage_path="/custom/path")
```

---

## Integration with Agent Runner

When loading agents via `AgentRunner.load()`, you can tag them to
workflows using the registry. A typical integration pattern:

```python
from framework.runner import AgentRunner
from framework.workflows import WorkflowRegistry, WorkflowCategory

# Load the agent
runner = AgentRunner.load("exports/support_ticket_agent")

# Register in workflow
registry = WorkflowRegistry()
registry.map_agent(
    agent_id=runner.graph.id,
    agent_name="Support Ticket Agent",
    workflow_ids=["customer-support-flow"],
)
```

---

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Workflow schemas, registry, agent tagging, dashboard API | ✅ Available |
| 2 | CLI commands (`hive workflows list`, `hive workflows map`) | 🗓 Planned |
| 3 | TUI dashboard integration | 🗓 Planned |
| 4 | Enterprise tool integrations (CRM, Slack, ticketing) | 🗓 Planned |
| 5 | Workflow analytics (trends, bottlenecks) | 🗓 Planned |

---

## See Also

- [Configuration Guide](./configuration.md) — Global and per-agent settings
- [Getting Started](./getting-started.md) — First-time setup
- [Environment Setup](./environment-setup.md) — Installation guide
