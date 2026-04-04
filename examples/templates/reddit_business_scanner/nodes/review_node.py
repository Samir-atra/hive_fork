from framework.graph import NodeSpec

review_node = NodeSpec(
    id="review-leads",
    name="Review Leads",
    description="Present leads and drafts for human approval (HITL).",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=["leads_with_drafts"],
    output_keys=["approved_leads", "skipped_leads", "status", "feedback"],
    nullable_output_keys=["feedback", "approved_leads", "skipped_leads"],
    tools=[],
    system_prompt="""\
Present the scored leads and their drafted outreach messages to the user for review.

**STEP 1 — Present (text only, NO tool calls):**
Display the leads, their scores, reasoning, and drafts. Ask the user:
1. Which leads do you approve?
2. Do you want to edit any drafts?
3. Which leads should be skipped?

**STEP 2 — After user responds, call set_output:**
- Process the user's feedback.
- set_output("approved_leads", list_of_approved_leads_with_any_edits)
- set_output("status", "approved") if they are ready to proceed with actions.
- set_output("status", "revise") and set_output("feedback", "...") if significant revisions to drafts are requested across the board.
""",
)
