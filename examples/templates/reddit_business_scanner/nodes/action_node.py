from framework.graph import NodeSpec

action_node = NodeSpec(
    id="take-action",
    name="Take Action on Approved Leads",
    description="Save approved leads to Airtable or send email outreach.",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["approved_leads"],
    output_keys=["action_summary"],
    tools=["airtable_create_records", "send_email"],
    system_prompt="""\
You are an execution agent.
Your task is to take action on human-approved Reddit leads.

## Instructions
1. For each lead in `approved_leads`:
   - Save the lead details (subreddit, title, url, score, reasoning, draft outreach) to Airtable using `airtable_create_records`.
   - OR send the outreach via email using `send_email` if requested.
2. Provide a summary of the actions taken.

Example:
```python
set_output("action_summary", {"saved_to_airtable": 3, "emails_sent": 0})
```
""",
)
