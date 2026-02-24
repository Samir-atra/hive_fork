from framework.graph import NodeSpec

classify_intent_node = NodeSpec(
    id="classify-intent",
    name="Classify Intent Node",
    description="Evaluates each email to classify its intent.",
    reads=["emails"],
    writes=["classified_emails"],
    system_prompt=(
        "Analyze the provided emails and classify their intent. "
        "Use categories such as: inquiry, support, meeting_request, spam, or newsletter. "
        "Return the classified list as 'classified_emails'."
    )
)
