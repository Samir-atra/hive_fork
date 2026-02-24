from framework.graph import NodeSpec

fetch_emails_node = NodeSpec(
    id="fetch-emails",
    name="Fetch Emails Node",
    description="Fetches recent unread incoming emails using Gmail API.",
    reads=["max_emails"],
    writes=["emails"],
    system_prompt=(
        "You are an email fetching assistant. "
        "Use the provided tools to extract unread incoming emails. "
        "Return the list of emails in the 'emails' variable."
    )
)
