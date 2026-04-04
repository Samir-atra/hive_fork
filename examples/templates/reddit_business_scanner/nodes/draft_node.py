from framework.graph import NodeSpec

draft_node = NodeSpec(
    id="draft-outreach",
    name="Draft Outreach",
    description="Draft personalized outreach messages for the scored leads.",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["scored_leads"],
    output_keys=["leads_with_drafts"],
    tools=[],
    system_prompt="""\
You are an expert sales copywriter.
Your task is to write personalized, non-spammy outreach messages for a list of Reddit leads.

## Instructions
1. For each lead in `scored_leads`:
   - Read the title, content, reasoning, and enriched data.
   - Draft a short, helpful, and contextual outreach message.
   - Ensure the tone is helpful, curious, and not overly sales-pushy.
   - Attach the draft to the lead object.
2. Save the updated leads list.

Example:
```python
set_output("leads_with_drafts", updated_leads)
```
""",
)
