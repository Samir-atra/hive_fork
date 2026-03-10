"""Node definitions for HR Onboarding Orchestrator.

This module defines the workflow nodes:
- intake_node: Collect new hire details
- monitor_envelope_node: Poll DocuSign for offer letter status
- action_fanout_node: Create tasks and send welcome email when signed
- escalation_node: Send Slack alert if not signed within timeout
- complete_node: Finalize onboarding workflow
"""

from framework.graph import NodeSpec

INTAKE_SYSTEM_PROMPT = """\
You are the HR Onboarding Intake Assistant.
Collect new hire information to begin the onboarding process.

**STEP 1 — Collect required information:**
Use ask_user to gather:
1. Candidate name
2. Candidate email address
3. Position/Job title
4. Department
5. Start date
6. DocuSign envelope ID (if available)

**STEP 2 — After collecting all information, call set_output:**
- set_output("candidate_name", "Full Name")
- set_output("candidate_email", "email@example.com")
- set_output("position", "Job Title")
- set_output("department", "Department Name")
- set_output("start_date", "YYYY-MM-DD")
- set_output("envelope_id", "docusign-envelope-id")
- set_output("status", "pending")
"""

MONITOR_ENVELOPE_SYSTEM_PROMPT = """\
You are the DocuSign Envelope Monitor. Check the status of the offer letter envelope.

**STEP 1 — Check envelope status:**
Use docusign_get_envelope_status with the envelope_id from memory
to check if the offer letter has been signed.

**STEP 2 — Determine next action:**
- If status is "completed" (signed): Call set_output with status="signed"
- If status is "declined": Call set_output with status="declined"
- If status is still "sent" or "delivered" (pending): Check elapsed time
  - If elapsed_hours >= 48: Call set_output with status="escalate"
  - Otherwise: Call set_output with status="pending" and poll_again="true"

**STEP 3 — Call set_output:**
- set_output("envelope_status", "signed|declined|pending|escalate")
- set_output("status", "signed|declined|pending|escalate")
- set_output("poll_again", "true|false") (true if still pending and not escalated)
- set_output("elapsed_hours", hours as string)
"""

ACTION_FANOUT_SYSTEM_PROMPT = """\
You are the Onboarding Action Orchestrator.
When an offer letter is signed, create tasks and send communications.

**STEP 1 — Create Monday.com tasks:**
1. IT Setup Task:
   Use monday_create_item with:
   - board_id: "IT_REQ"
   - item_name: "Laptop setup for {candidate_name}"
   - column_values: {"dept": "{department}", "start_date": "{start_date}", "type": "equipment"}

2. Payroll Task:
   Use monday_create_item with:
   - board_id: "FINANCE_ONBOARDING"
   - item_name: "{candidate_name} - {position}"
   - column_values: {"department": "{department}", "start_date": "{start_date}"}

**STEP 2 — Send welcome email:**
Use send_email with:
- to: {candidate_email}
- subject: "Welcome to the Team! Your Onboarding Guide"
- body: Include start date, first day instructions, and key contacts

**STEP 3 — Call set_output:**
- set_output("it_task_created", "true")
- set_output("payroll_task_created", "true")
- set_output("welcome_email_sent", "true")
- set_output("status", "completed")
"""

ESCALATION_SYSTEM_PROMPT = """\
You are the Onboarding Escalation Handler.
Alert the recruiting team when an offer letter hasn't been signed
within the expected timeframe.

**STEP 1 — Send Slack notification:**
Use slack_send_message with:
- channel: "#recruiting" (or configured recruiter channel)
- text: Alert about unsigned offer letter including:
  - Candidate name
  - Position
  - Days since offer sent
  - Link to DocuSign envelope (if available)

**STEP 2 — Call set_output:**
- set_output("escalation_sent", "true")
- set_output("status", "escalated")
"""

COMPLETE_SYSTEM_PROMPT = """\
You are the Onboarding Completion Handler. Summarize the completed onboarding workflow.

**STEP 1 — Compile summary:**
Gather all information from memory:
- Candidate details (name, email, position, department, start date)
- DocuSign envelope status
- Tasks created (IT, Payroll)
- Welcome email sent status
- Any escalations

**STEP 2 — Create final summary and save:**
Use save_data to save a summary file:
- filename: "onboarding_{candidate_name}_{start_date}.json"
- content: JSON object with all workflow details

**STEP 3 — Call set_output:**
- set_output("workflow_status", "completed")
- set_output("summary_file", filename)
"""

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect new hire details to begin onboarding process",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=[],
    output_keys=[
        "candidate_name",
        "candidate_email",
        "position",
        "department",
        "start_date",
        "envelope_id",
        "status",
    ],
    nullable_output_keys=[],
    system_prompt=INTAKE_SYSTEM_PROMPT,
    tools=[],
)

monitor_envelope_node = NodeSpec(
    id="monitor_envelope",
    name="Monitor Envelope",
    description="Poll DocuSign for offer letter signing status",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["envelope_id", "candidate_name"],
    output_keys=["envelope_status", "status", "poll_again", "elapsed_hours"],
    nullable_output_keys=[],
    system_prompt=MONITOR_ENVELOPE_SYSTEM_PROMPT,
    tools=["docusign_get_envelope_status"],
)

action_fanout_node = NodeSpec(
    id="action_fanout",
    name="Action Fan-out",
    description="Create IT/Payroll tasks and send welcome email when signed",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=[
        "candidate_name",
        "candidate_email",
        "position",
        "department",
        "start_date",
        "envelope_status",
    ],
    output_keys=[
        "it_task_created",
        "payroll_task_created",
        "welcome_email_sent",
        "status",
    ],
    nullable_output_keys=[],
    system_prompt=ACTION_FANOUT_SYSTEM_PROMPT,
    tools=["monday_create_item", "send_email"],
)

escalation_node = NodeSpec(
    id="escalation",
    name="Escalation",
    description="Send Slack alert to recruiter for unsigned offers",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["candidate_name", "position", "envelope_id", "elapsed_hours"],
    output_keys=["escalation_sent", "status"],
    nullable_output_keys=[],
    system_prompt=ESCALATION_SYSTEM_PROMPT,
    tools=["slack_send_message"],
)

complete_node = NodeSpec(
    id="complete",
    name="Complete",
    description="Finalize onboarding workflow and save summary",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=[
        "candidate_name",
        "candidate_email",
        "position",
        "department",
        "start_date",
        "envelope_status",
        "it_task_created",
        "payroll_task_created",
        "welcome_email_sent",
        "escalation_sent",
    ],
    output_keys=["workflow_status", "summary_file"],
    nullable_output_keys=["escalation_sent"],
    system_prompt=COMPLETE_SYSTEM_PROMPT,
    tools=["save_data"],
)

__all__ = [
    "intake_node",
    "monitor_envelope_node",
    "action_fanout_node",
    "escalation_node",
    "complete_node",
]
