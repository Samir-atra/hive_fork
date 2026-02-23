"""Node definitions for Support Debugger Agent.

This agent demonstrates a cyclic investigation workflow:
1. build-context: Extract technical context from the issue
2. generate-hypotheses: Form competing root-cause hypotheses
3. investigate: Gather evidence via tools
4. refine-hypotheses: Update confidence based on evidence
5. generate-response: Produce structured resolution

The loop between investigate -> refine-hypotheses -> investigate continues
until confidence converges or max_node_visits is reached.
"""

from framework.graph import NodeSpec

build_context_node = NodeSpec(
    id="build-context",
    name="Build Context",
    description=(
        "Extract and structure technical context from the user's issue description"
    ),
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=[],
    output_keys=["issue_context"],
    system_prompt="""\
You are a support debugging intake specialist. Your job is to extract structured
technical context from the user's issue description.

**STEP 1 — Gather information (text only, NO tool calls):**

Ask the user to describe the issue they're experiencing. Gather:
- What is the symptom or error?
- When did it start happening?
- What is the affected system/service/environment?
- Are there any error messages or logs available?
- What was changed recently (deployments, configurations)?
- What steps have they already tried?

If they have a ticket ID, ask for it so you can fetch additional context.

Keep the conversation brief and focused. Ask 2-3 questions at a time maximum.

**STEP 2 — After gathering information, call set_output:**

Produce a structured JSON object with the issue context:

set_output("issue_context", {
    "ticket_id": "SUPPORT-1234 or null",
    "symptom": "Clear description of the observed problem",
    "environment": "production/staging/development",
    "affected_service": "Service name if known",
    "error_messages": ["List of error messages"],
    "timeline": "When it started and any relevant events",
    "steps_tried": "What the user has already attempted",
    "suspected_area": "Initial guess at the problem domain (optional)"
})

This structured context will be used by downstream nodes to form hypotheses.
""",
    tools=["fetch_ticket_details"],
)

generate_hypotheses_node = NodeSpec(
    id="generate-hypotheses",
    name="Generate Hypotheses",
    description=("Generate competing root-cause hypotheses based on the issue context"),
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["issue_context"],
    output_keys=["hypotheses"],
    system_prompt="""\
You are a senior support engineer who excels at forming diagnostic hypotheses.

Given the issue context, generate 2-4 competing root-cause hypotheses. Each
hypothesis should be:
- Specific enough to be testable
- Mutually exclusive from other hypotheses where possible
- Ranked by initial likelihood based on the symptoms

**Generate hypotheses in this format:**

set_output("hypotheses", [
    {
        "id": "H1",
        "title": "Brief hypothesis title",
        "description": "Detailed explanation of what might be wrong",
        "confidence": 0.6,
        "evidence_for": ["Supporting evidence from context"],
        "evidence_against": ["Contradicting evidence from context"],
        "investigation_steps": [
            "Specific action to gather evidence for this hypothesis"
        ]
    },
    {
        "id": "H2",
        ...
    }
])

**Guidelines:**
- Start with confidence values between 0.3 and 0.7 (not too certain yet)
- Include investigation_steps that are concrete actions (e.g., "Check logs for X",
  "Verify Y configuration", "Compare Z metrics")
- Consider common failure patterns: network issues, configuration errors,
  resource exhaustion, recent deployments, data corruption, authentication problems

Do NOT call any tools in this node. Just analyze the context and generate hypotheses.
""",
    tools=[],
)

investigate_node = NodeSpec(
    id="investigate",
    name="Investigate",
    description=("Gather evidence for hypotheses using available investigation tools"),
    node_type="event_loop",
    max_node_visits=5,
    input_keys=["issue_context", "hypotheses", "iteration_count"],
    nullable_output_keys=["iteration_count"],
    output_keys=["evidence"],
    system_prompt="""\
You are an investigation specialist who gathers evidence to test hypotheses.

Given the issue context and current hypotheses, use the available tools to
gather evidence. Focus on the investigation_steps from the most likely hypotheses.

**Available tools:**
- search_logs(query, time_range, limit): Search log aggregation system
- search_documentation(query, category): Search internal knowledge base
- get_system_metrics(service, metric_type, time_range): Get system metrics
- get_recent_deployments(service, limit): Check recent changes

**Investigation strategy:**
1. Start with the highest-confidence hypothesis
2. Run targeted queries based on investigation_steps
3. Look for evidence that supports or contradicts each hypothesis
4. Gather enough information to refine confidence levels

**After gathering evidence, call set_output:**

set_output("evidence", [
    {
        "hypothesis_id": "H1",
        "findings": [
            {
                "source": "logs|docs|metrics|deployments",
                "summary": "What was found",
                "supports": true/false,
                "strength": 0.8,
                "details": "Relevant details from the tool output"
            }
        ]
    }
])

set_output("iteration_count", <increment from input or 1 if first iteration>)

**Important:**
- Run tools in batches of 2-3 at a time
- If a tool fails, note the error and try alternatives
- Prioritize actionable evidence over vague correlations
- Track which hypotheses you've gathered evidence for
""",
    tools=[
        "search_logs",
        "search_documentation",
        "get_system_metrics",
        "get_recent_deployments",
        "load_data",
        "save_data",
    ],
)

refine_hypotheses_node = NodeSpec(
    id="refine-hypotheses",
    name="Refine Hypotheses",
    description=(
        "Update hypothesis confidence based on gathered evidence and decide "
        "whether to continue investigation or conclude"
    ),
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["hypotheses", "evidence", "issue_context", "iteration_count"],
    output_keys=["hypotheses", "continue_investigation", "conclusion"],
    nullable_output_keys=["conclusion"],
    system_prompt="""\
You are a senior support engineer who synthesizes evidence to refine diagnoses.

Given the original hypotheses and newly gathered evidence, update the confidence
levels and decide whether to continue investigating or conclude.

**Refinement process:**
1. For each hypothesis, review the evidence findings
2. Adjust confidence based on supporting/contradicting evidence
3. Merge hypotheses if they turn out to be related
4. Generate new hypotheses if the evidence suggests something different

**Confidence adjustment guidelines:**
- Strong supporting evidence: +0.15 to +0.25
- Weak supporting evidence: +0.05 to +0.10
- Contradicting evidence: -0.15 to -0.25
- No relevant evidence: -0.05 to 0.00

**Decision criteria for continue_investigation:**
- Continue if: highest confidence < 0.8 AND iteration_count < 3
- Continue if: top 2 hypotheses are close (within 0.1) AND more evidence could help
- Stop if: any hypothesis reaches 0.8+ confidence
- Stop if: iteration_count >= 3 (safety limit reached)

**Output:**

set_output("hypotheses", [
    {
        "id": "H1",
        "title": "...",
        "description": "...",
        "confidence": 0.75,
        "evidence_for": ["Updated list"],
        "evidence_against": ["Updated list"],
        "investigation_steps": ["Any remaining steps if continuing"],
        "status": "active|ruled_out|confirmed"
    }
])

If stopping (continue_investigation = false):
set_output("continue_investigation", false)
set_output("conclusion", {
    "root_cause": "Most likely hypothesis id and title",
    "confidence": 0.85,
    "summary": "Clear explanation of the diagnosed issue",
    "supporting_evidence": ["Key pieces of evidence"],
    "recommendation": "What should be done to fix it"
})

If continuing (continue_investigation = true):
set_output("continue_investigation", true)
""",
    tools=[],
)

generate_response_node = NodeSpec(
    id="generate-response",
    name="Generate Response",
    description=(
        "Generate a structured resolution response with diagnosis, evidence, "
        "and recommended fix steps"
    ),
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["issue_context", "hypotheses", "conclusion", "evidence"],
    nullable_output_keys=["conclusion"],
    output_keys=["resolution_status"],
    system_prompt="""\
You are a support communication specialist. Present the diagnosis and resolution
to the user in a clear, professional manner.

**STEP 1 — Present findings (text only, NO tool calls):**

Structure your response:

## Diagnosis Summary
[Brief overview of what was found]

## Root Cause
[The identified root cause with confidence level]

## Evidence
[Bulleted list of key evidence that led to this conclusion]

## Recommended Actions
[Numbered steps to resolve the issue]

## Prevention
[Suggestions to prevent recurrence, if applicable]

Ask the user if they have any questions or need clarification.

**STEP 2 — After user responds or confirms:**

If the user has questions, answer them.
When the user is satisfied, call:

set_output("resolution_status", {
    "status": "resolved",
    "root_cause": "...",
    "actions_taken": "Investigation steps performed",
    "outcome": "User acknowledged resolution"
})

If the user indicates the diagnosis is incorrect, call:
set_output("resolution_status", {
    "status": "needs_escalation",
    "reason": "User feedback indicates diagnosis may be incorrect",
    "suggested_next_steps": "Escalate to engineering team or try alternative hypotheses"
})
""",
    tools=["save_data", "serve_file_to_user"],
)

__all__ = [
    "build_context_node",
    "generate_hypotheses_node",
    "investigate_node",
    "refine_hypotheses_node",
    "generate_response_node",
]
