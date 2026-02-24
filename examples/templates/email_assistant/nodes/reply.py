from framework.graph import NodeSpec

generate_reply_node = NodeSpec(
    id="generate-reply",
    name="Generate Reply Node",
    description="Drafts intelligent replies for actionable intents.",
    reads=["classified_emails"],
    writes=["replied_emails"],
    system_prompt=(
        "For any email with an actionable intent (e.g., inquiry, support, meeting_request), "
        "draft an intelligent and polite reply. "
        "Append the drafted reply to the email data and save it as 'replied_emails'."
    )
)
