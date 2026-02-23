# AI Agent Recommendations Engine

Automatically suggests which agents to deploy, highlights under-utilised
capacity, identifies workflow gaps, and scores predicted impact — so
teams can optimise AI agent adoption without guesswork.

> **Status:** Phase 1 (rule-based engine).  Six analysis passes are
> available now.  ML-based predictive scoring and dashboard integration
> are planned for later phases.

---

## Quick Start

```python
from framework.recommendations import (
    RecommendationsEngine,
    AgentProfile,
    WorkflowProfile,
)

engine = RecommendationsEngine()

report = engine.analyse(
    agents=[
        AgentProfile(
            agent_id="support-agent",
            agent_name="Customer Support Agent",
            capabilities=["web_search", "email", "ticket_management"],
            total_runs=200,
            successful_runs=185,
            workflow_ids=["cs-flow"],
        ),
        AgentProfile(
            agent_id="sales-agent",
            agent_name="Sales Agent",
            capabilities=["crm", "email", "scheduling"],
            total_runs=50,
            successful_runs=45,
        ),
    ],
    workflows=[
        WorkflowProfile(
            workflow_id="cs-flow",
            workflow_name="Customer Support",
            required_capabilities=["web_search", "email", "ticket_management"],
            current_agent_ids=["support-agent"],
        ),
        WorkflowProfile(
            workflow_id="sales-flow",
            workflow_name="Sales Pipeline",
            required_capabilities=["crm", "email", "scheduling", "analytics"],
        ),
    ],
)

for rec in report.recommendations:
    print(f"[{rec.priority}] {rec.title}")
    print(f"  Impact: {rec.impact.overall:.0%}  Confidence: {rec.impact.confidence:.0%}")
    print(f"  {rec.description}\n")
```

---

## Analysis Passes

The engine runs six independent analysis passes and merges the results
into a single prioritised report:

### 1. Agent-for-Workflow Suggestions (`AGENT_FOR_WORKFLOW`)

Matches unassigned agents to workflows based on **capability overlap**
and **historical success rate**.

| Criteria | Threshold |
|----------|-----------|
| Minimum capability match | ≥ 50% of workflow's required capabilities |
| Already-assigned agents | Excluded |

### 2. Underutilised Agents (`UNDERUTILISED_AGENT`)

Flags agents that are mapped to workflows but have very few executions.

| Criteria | Threshold |
|----------|-----------|
| Maximum total runs | ≤ 5 |
| Must be mapped | At least one workflow |

### 3. High Performers (`HIGH_PERFORMER`)

Highlights agents with consistently strong success rates.

| Criteria | Threshold |
|----------|-----------|
| Minimum total runs | ≥ 10 |
| Minimum success rate | ≥ 85% |

### 4. Workflow Gaps (`WORKFLOW_GAP`)

Identifies two types of gaps:
- **Unmapped workflows** — no agents assigned at all (HIGH priority)
- **Capability gaps** — assigned agents don't cover all required capabilities

### 5. Agent Combinations (`AGENT_COMBINATION`)

Suggests **pairs** of agents whose combined capabilities fully cover a
workflow's requirements when no single agent can.

### 6. Performance Improvements (`PERFORMANCE_IMPROVEMENT`)

Flags agents or workflows with below-threshold success rates.

| Criteria | Threshold |
|----------|-----------|
| Minimum total runs | ≥ 10 |
| Maximum success rate | < 50% |

---

## Impact Scoring

Every recommendation includes an `ImpactScore`:

| Field | Range | Description |
|-------|-------|-------------|
| `overall` | 0.0–1.0 | Composite relevance score |
| `time_savings_pct` | 0–100 | Estimated time savings |
| `efficiency_gain_pct` | 0–100 | Estimated efficiency improvement |
| `confidence` | 0.0–1.0 | How confident the estimate is |
| `rationale` | string | Human-readable explanation |

Confidence is determined by sample size:
- ≥ 50 runs → 0.8
- ≥ 10 runs → 0.5
- < 10 runs → 0.2

---

## API Reference

### Input Models

```python
AgentProfile(
    agent_id="...",
    agent_name="...",
    capabilities=["web_search", "email"],
    total_runs=100,
    successful_runs=90,
    failed_runs=10,
    avg_latency_ms=250.0,
    total_tokens=50000,
    workflow_ids=["wf-1"],
    tags=["tier-1"],
)

WorkflowProfile(
    workflow_id="...",
    workflow_name="...",
    category="customer_support",
    required_capabilities=["web_search", "email"],
    current_agent_ids=["agent-1"],
    total_runs=200,
    successful_runs=180,
)
```

### Engine

```python
engine = RecommendationsEngine()
report = engine.analyse(agents=[...], workflows=[...])
```

### Output Models

```python
report.recommendations       # list[Recommendation], sorted by impact
report.total_agents_analysed  # int
report.total_workflows_analysed  # int
report.generated_at           # ISO timestamp

# Each recommendation:
rec.id         # Unique ID
rec.type       # RecommendationType enum
rec.priority   # HIGH / MEDIUM / LOW
rec.status     # PENDING / ACCEPTED / DISMISSED / APPLIED
rec.title      # One-line summary
rec.description  # Detailed explanation
rec.agent_id   # Related agent (if applicable)
rec.workflow_id  # Related workflow (if applicable)
rec.impact     # ImpactScore
rec.metadata   # dict with extra structured data
```

---

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Rule-based engine, schemas, 6 analysis passes, tests | ✅ Available |
| 2 | Dashboard integration (display recommendations in TUI) | 🗓 Planned |
| 3 | ML-based impact scoring (train on historical run data) | 🗓 Planned |
| 4 | Peer/community-based recommendations | 🗓 Planned |
| 5 | Automated recommendation application via CLI | 🗓 Planned |

---

## See Also

- [Workflow Mapping](./workflow-mapping.md) — Map agents to business workflows
- [Configuration Guide](./configuration.md) — Global and per-agent settings
- [Getting Started](./getting-started.md) — First-time setup
