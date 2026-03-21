# Inbound Lead Sentinel Agent

The **Inbound Lead Sentinel** is a Goal-Driven multi-node agent built to combat "lead leakage" by automatically handling inbound demo requests. It validates, enriches, scores, and ultimately routes high-quality inbound requests directly into Salesforce to protect margins and accelerate the sales pipeline.

## Features

- **Automatic Enrichment**: Reaches out to Apollo.io (mocked) to bring in firmographic data like company size, industry, and revenue.
- **ICP Scoring Engine**: Evaluates enriched leads against your Ideal Customer Profile using a dynamic scoring threshold (Queen Bee engine architecture).
- **Salesforce Routing**: High-scoring leads are dynamically converted into Opportunities in Salesforce.
- **Circuit Breaker Mechanism**: Avoids API runaway costs or token bloat when lead volume spikes unexpectedly.

## Architecture

This Sentinel agent utilizes a 4-node execution graph within the Hive framework:

1. **Intake Node**: Fetches incoming demo requests and triggers the circuit breaker if the load exceeds the configured batch size limit.
2. **Enrich Node**: Augments lead records with critical domain and company data based on the prospect's email structure.
3. **Score Node**: Assigns an actionable priority score (0-100) using customized firmographic factor weights.
4. **Route Node**: Splits leads into high-priority Opportunities or standard rejected queues.

## Setup & Running

This template can be executed or tested directly within the core framework via the CLI or instantiated via Python API:

```python
from examples.templates.inbound_lead_sentinel.agent import InboundLeadSentinel

# Instantiate agent
agent = InboundLeadSentinel()

# Run agent payload
result = await agent.run({
    "new_leads": [
        {"email": "ceo@enterprise.com", "name": "Jane Doe"}
    ],
    "max_leads_per_batch": 50,
    "icp_score_threshold": 70,
})

print(result.output)
```

## Testing

You can verify the agent logic locally by running the comprehensive pytest suite:

```bash
cd core && uv run pytest ../examples/templates/inbound_lead_sentinel/tests/
```
