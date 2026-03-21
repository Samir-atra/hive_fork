"""Nodes for the Inbound Lead Sentinel."""

from typing import Any

from framework.graph.executor import ExecutionResult
from framework.graph.node import NodeContext, NodeSpec


async def _intake_leads(context: NodeContext, state: Any) -> ExecutionResult:
    """Intake node for demo requests."""
    # Simulates pulling new demo requests from an intake form or webhook
    leads = context.memory.read("new_leads") or []
    max_leads = context.memory.read("max_leads_per_batch") or 50

    if len(leads) > max_leads:
        context.memory.write("circuit_breaker_tripped", True)
        return ExecutionResult(success=True)

    context.memory.write("circuit_breaker_tripped", False)
    context.memory.write("processing_leads", leads)
    return ExecutionResult(success=True)


async def _enrich_leads(context: NodeContext, state: Any) -> ExecutionResult:
    """Enrich node via Apollo.io."""
    tripped = context.memory.read("circuit_breaker_tripped")
    if tripped:
        return ExecutionResult(success=True)

    leads = context.memory.read("processing_leads") or []
    enriched = []

    # Mock Apollo.io enrichment logic
    for lead in leads:
        # Simulate an API call
        email = lead.get("email", "")
        domain = email.split("@")[-1] if "@" in email else "unknown.com"

        enrichment_data = {
            "company_size": 1000 if domain in ["enterprise.com", "megacorp.com"] else 50,
            "industry": "Tech" if domain == "techstartup.io" else "Other",
            "revenue": "$10M+" if domain in ["enterprise.com", "megacorp.com"] else "<$1M",
        }

        enriched_lead = lead.copy()
        enriched_lead.update(enrichment_data)
        enriched.append(enriched_lead)

    context.memory.write("enriched_leads", enriched)
    return ExecutionResult(success=True)


async def _score_leads(context: NodeContext, state: Any) -> ExecutionResult:
    """Score node using Queen Bee engine logic."""
    tripped = context.memory.read("circuit_breaker_tripped")
    if tripped:
        return ExecutionResult(success=True)

    leads = context.memory.read("enriched_leads") or []
    scored = []

    # Dynamic ICP logic
    for lead in leads:
        score = 0

        # Scoring factors
        if lead.get("company_size", 0) > 500:
            score += 40
        elif lead.get("company_size", 0) > 50:
            score += 20

        if lead.get("industry") == "Tech":
            score += 30

        if lead.get("revenue") == "$10M+":
            score += 30

        scored_lead = lead.copy()
        scored_lead["icp_score"] = min(score, 100)  # Cap at 100
        scored.append(scored_lead)

    context.memory.write("scored_leads", scored)
    return ExecutionResult(success=True)


async def _route_leads(context: NodeContext, state: Any) -> ExecutionResult:
    """Route node to Salesforce."""
    tripped = context.memory.read("circuit_breaker_tripped")
    if tripped:
        return ExecutionResult(success=True)

    leads = context.memory.read("scored_leads") or []
    threshold = context.memory.read("icp_score_threshold") or 75

    routed = []
    rejected = []

    for lead in leads:
        if lead.get("icp_score", 0) >= threshold:
            # Mock Salesforce Opportunity creation
            routed.append(lead)
        else:
            rejected.append(lead)

    context.memory.write("routed_leads", routed)
    context.memory.write("rejected_leads", rejected)

    return ExecutionResult(success=True)


# Important fix: We need to set mock_response to bypass the event_loop judge stalling
intake_node = NodeSpec(
    id="intake",
    name="Intake Demo Requests",
    description="Fetches inbound demo requests and enforces the circuit breaker batch limit",
    node_type="event_loop",
    execute_func=_intake_leads,
    output_keys=["circuit_breaker_tripped", "processing_leads"],
)

enrich_node = NodeSpec(
    id="enrich",
    name="Enrich Lead Data",
    description="Uses Apollo.io (mocked) to add firmographic data to the lead",
    node_type="event_loop",
    execute_func=_enrich_leads,
    output_keys=["enriched_leads"],
)

score_node = NodeSpec(
    id="score",
    name="Score Leads",
    description="Scores enriched leads against the Ideal Customer Profile (ICP)",
    node_type="event_loop",
    execute_func=_score_leads,
    output_keys=["scored_leads"],
)

route_node = NodeSpec(
    id="route",
    name="Route Leads to Salesforce",
    description="Creates Salesforce opportunities for leads exceeding the ICP score threshold",
    node_type="event_loop",
    execute_func=_route_leads,
    output_keys=["routed_leads", "rejected_leads"],
)
