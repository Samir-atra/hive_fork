"""Node definitions for Commercial CRM Agent."""

from framework.graph import NodeSpec

# Node 1: Intake (client-facing)
intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Gather CRM query criteria and messaging channel destination from user",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["workflow_complete"],
    output_keys=["crm_criteria"],
    nullable_output_keys=["workflow_complete"],
    success_criteria="User provides a valid CRM query and messaging destination.",
    system_prompt="""\
You are an intake specialist for a Revenue/Support Agent. Your ONLY job is to gather filter criteria for CRM lookup and the destination messaging channel.

If the user has already provided criteria in their message, IMMEDIATELY call:
set_output("crm_criteria", {"crm_query": "...", "messaging_destination": "..."})

DO NOT:
- Read files
- Search files
- List directories
- Try to execute CRM commands directly

If you need more information, ask ONE brief question. Otherwise, call set_output immediately.

After workflow_complete, acknowledge and ask for the next task.
""",
    tools=[],
)

# Node 2: CRM Search (autonomous)
crm_search_node = NodeSpec(
    id="crm_search",
    name="CRM Search",
    description="Search the CRM for leads or deals matching the criteria",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["crm_criteria"],
    output_keys=["crm_results", "messaging_destination"],
    nullable_output_keys=[],
    success_criteria="Found relevant records from the CRM based on the criteria.",
    system_prompt="""\
You are a CRM lookup agent. Your task is to query the connected CRM (e.g., via the provided MCP tool) for leads, contacts, or deals matching the user's intent.

## Workflow:
1. Parse the crm_query from the crm_criteria.
2. Formulate the appropriate API call or tool invocation using the available CRM tools (e.g., hubspot_search_contacts).
3. Extract relevant information from the CRM results (e.g., names, emails, last contacted dates, deal amounts).
4. Call set_output with the formatted results.

## Output:
set_output("crm_results", <formatted string or JSON list of results>)
set_output("messaging_destination", <the messaging_destination from crm_criteria>)

If no matching records are found, output an empty result or a clear message indicating none were found.
""",
    tools=[],  # MCP tools injected at runtime
)

# Node 3: Messaging (autonomous)
messaging_node = NodeSpec(
    id="messaging",
    name="Messaging Notification",
    description="Format and dispatch the CRM results to a messaging channel",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=0,
    input_keys=["crm_results", "messaging_destination"],
    output_keys=["workflow_complete"],
    nullable_output_keys=["workflow_complete"],
    success_criteria="Formatted notification sent to the messaging platform.",
    system_prompt="""\
You are a Messaging Dispatcher agent. Your task is to take the retrieved CRM results and send a formatted alert to the connected messaging platform (e.g., Slack or Teams).

## Workflow:
1. Review the crm_results.
2. Format the results into a clear, professional notification message (use markdown or blocks if applicable).
3. Identify the target channel or user from messaging_destination.
4. Call the appropriate messaging tool (e.g., slack_post_message) to send the notification.
5. After successfully sending, call set_output("workflow_complete", True).

## Output:
set_output("workflow_complete", True)

Ensure the message is easy to read for sales or support teams.
""",
    tools=[],  # MCP tools injected at runtime
)

__all__ = ["intake_node", "crm_search_node", "messaging_node"]
