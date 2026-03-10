# Business Process Executor

An autonomous business process agent that executes multi-step operations from a single goal statement.

## Overview

This agent demonstrates Hive's outcome-driven execution model:

- **Outcome-first execution**: No clarification-first UX. The agent proceeds with reasonable assumptions.
- **Goal → Graph → Outcome**: Clear mapping from business goal to execution to results.
- **Human-in-the-loop at decision boundaries**: Only asks for input at critical decision points.
- **Business-readable summaries**: All outputs use business terminology, not technical jargon.
- **Graceful failure handling**: Explains issues in business terms, adapts, and retries.

## Quick Start

```bash
# Start the agent in interactive mode
cd core
uv run python -m business_process_executor

# Run with a specific goal
uv run python -m business_process_executor run --goal "Follow up with all leads from last week's webinar"

# Run an example
uv run python -m business_process_executor example --example webinar-followup
```

## Example Goals

The agent can handle business goals like:

1. **"Follow up with all leads from last week's webinar"**
   - Parses objective: Contact leads, schedule demos
   - Plans: Fetch lead list, draft emails, send follow-ups
   - Executes: Uses Gmail, Calendar tools
   - Decision point: Which leads to prioritize?
   - Summary: X leads contacted, Y demos scheduled

2. **"Process customer escalations and resolve them"**
   - Parses objective: Handle escalations queue
   - Plans: Fetch escalations, categorize, respond
   - Executes: Uses communication tools
   - Decision point: Escalate to manager if unresolved?
   - Summary: X escalations resolved, Y pending

3. **"Generate Q4 revenue report and send to stakeholders"**
   - Parses objective: Create report, distribute
   - Plans: Gather data, format report, send
   - Executes: Uses data and email tools
   - Decision point: Which stakeholders to include?
   - Summary: Report generated and sent to X recipients

4. **"Onboard new customers from this week's acquisition"**
   - Parses objective: Set up new customers
   - Plans: Create accounts, send welcome, schedule training
   - Executes: Uses various platform tools
   - Decision point: Custom onboarding for VIP customers?
   - Summary: X customers onboarded successfully

## Architecture

```
┌─────────┐    ┌──────┐    ┌──────────┐    ┌─────────┐
│ Intake  │───►│ Plan │───►│ Execute  │───►│ Validate│
└─────────┘    └──────┘    └──────────┘    └─────────┘
     ▲                           │               │
     │                      ┌────┴────┐          │
     │                      ▼         ▼          ▼
     │                 ┌────────┐ ┌────────┐ ┌─────────┐
     │                 │ Decide │ │ Adapt  │ │Summarize│
     │                 └────────┘ └────────┘ └─────────┘
     │                      │         │
     └──────────────────────┴─────────┘
```

### Nodes

1. **Intake** - Accepts business goal in plain English, structures it
2. **Plan** - Generates execution plan with steps and decision points
3. **Execute** - Executes steps using available tools
4. **Decide** - Handles human-in-the-loop at decision boundaries
5. **Validate** - Checks outcomes against success criteria
6. **Adapt** - Handles failures with adaptation strategies
7. **Summarize** - Produces business-readable summary

### Key Features

- **No clarification-first UX**: Proceeds with reasonable assumptions
- **Decision boundaries only**: Human input only at critical points
- **Business language**: All communication uses business terminology
- **Adaptive retry**: Handles failures gracefully with alternative approaches
- **Clear summaries**: Business-readable results every time

## Configuration

Edit `config.py` to customize:

```python
max_execution_steps: int = 50        # Maximum steps per goal
decision_confidence_threshold: float = 0.75  # When to ask for input
max_retries_per_step: int = 3        # Retries before marking blocked
```

## Success Criteria

The agent is evaluated against:

1. **Goal achievement** (30%): >=80% completion
2. **Autonomous execution** (20%): <=3 human interventions
3. **Decision accuracy** (15%): >=90% precision on decision points
4. **Failure recovery** (15%): >=70% successful retries
5. **Summary quality** (10%): >=85% clarity score
6. **Time to value** (10%): <=5 minutes to first result

## Target Users

- Founders evaluating Hive for production use
- Ops teams automating business processes
- PMs exploring autonomous agents

## What This Agent Demonstrates

1. **Outcome-first execution** vs clarification-first UX
2. **Clear mapping** from goal → graph → outcome
3. **Business-level summaries** layered over observability
4. **Minimal human intervention** with smart decision boundaries
5. **Graceful failure handling** with business-friendly explanations
