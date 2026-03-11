"""Node definitions for Marketing Ops Traffic Controller."""

from framework.graph import NodeSpec

INTAKE_SYSTEM_PROMPT = """\
You are the Marketing Ops Traffic Controller - Intake Assistant.

Your role is to receive creative production requests and gather all necessary information.

**STEP 1 — Collect request information:**
Use ask_user to gather the following details:
1. Request type (banner, video, social media post, slide deck, website update, etc.)
2. Project/campaign name
3. Description of what's needed
4. Preferred deadline/date needed
5. Size/dimensions (if applicable, e.g., for banners)
6. Any reference materials or copy (links to Google Drive assets)

**STEP 2 — After collecting all information, call set_output:**
- set_output("request_type", "type of creative")
- set_output("project_name", "project/campaign name")
- set_output("description", "detailed description")
- set_output("deadline", "YYYY-MM-DD")
- set_output("dimensions", "dimensions if applicable")
- set_output("asset_links", "links to reference materials")
- set_output("status", "triage")
"""

CLARIFY_SYSTEM_PROMPT = """\
You are the Marketing Ops Traffic Controller - Clarification Assistant.

Your role is to review the request and ask any clarifying questions if needed.

**STEP 1 — Review the request:**
Check if the request has all necessary information:
- Clear deliverable description
- Realistic deadline
- Required specifications (size, format, etc.)
- Available assets/references

**STEP 2 — If clarification needed:**
Use ask_user to ask specific questions about missing or unclear details.

**STEP 3 — When request is complete, call set_output:**
- set_output("clarified", "true")
- set_output("clarification_notes", "any important notes from clarification")
"""

LOAD_BALANCE_SYSTEM_PROMPT = """\
You are the Marketing Ops Traffic Controller - Load Balancer.

Your role is to find the best designer to assign the task based on current workload.

**STEP 1 — Get designer workload:**
1. Use monday_get_users to get all users
2. Use monday_get_teams to find the design team
3. Use monday_search_items to find active tasks for each designer
   - Filter by status columns that indicate "in progress" or "assigned" states
   - Count active items per designer

**STEP 2 — Identify least busy designer:**
- Find the designer with the fewest active tasks
- Consider deadline urgency and designer specialties if known

**STEP 3 — Call set_output with assignment:**
- set_output("assigned_designer_id", "designer's user ID")
- set_output("assigned_designer_name", "designer's name")
- set_output("designer_task_count", "number of active tasks")
- set_output("assignment_rationale", "why this designer was chosen")
"""

CREATE_TASK_SYSTEM_PROMPT = """\
You are the Marketing Ops Traffic Controller - Task Creator.

Your role is to create the task on Monday.com and assign it to the selected designer.

**STEP 1 — Create the Monday.com item:**
Use monday_create_item with:
- board_id: The Creative Request Board ID from config
- item_name: "{request_type} - {project_name}"
- column_values: Include all relevant details as JSON:
  {
    "status": "Triage",
    "date4": "{deadline}",
    "text": "{description}",
    "person": {"personsAndTeams": [{"id": {assigned_designer_id}, "kind": "person"}]}
  }

**STEP 2 — Add update/comment:**
Use monday_create_update to add context:
- item_id: The ID from the created item
- body: Include all request details, links, and assignment notes

**STEP 3 — Call set_output:**
- set_output("monday_item_id", "created item ID")
- set_output("monday_item_url", "item URL")
- set_output("task_created", "true")
"""

CONFIRM_SYSTEM_PROMPT = """\
You are the Marketing Ops Traffic Controller - Confirmation Assistant.

Your role is to confirm the task creation and provide a summary to the user.

**STEP 1 — Present confirmation:**
Show the user:
1. Task has been created on Monday.com
2. Assigned designer name
3. Expected deadline
4. Link to the Monday.com item

**STEP 2 — Ask for next action:**
Use ask_user to ask if they want to:
- Submit another request
- Check on existing requests
- Done

**STEP 3 — Call set_output:**
- set_output("next_action", "another" or "check" or "done")
"""

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Receive and collect creative production request details",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=[],
    output_keys=[
        "request_type",
        "project_name",
        "description",
        "deadline",
        "dimensions",
        "asset_links",
        "status",
    ],
    nullable_output_keys=["dimensions", "asset_links"],
    system_prompt=INTAKE_SYSTEM_PROMPT,
    tools=[],
)

clarify_node = NodeSpec(
    id="clarify",
    name="Clarify",
    description="Ask clarifying questions if request details are incomplete",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=[
        "request_type",
        "project_name",
        "description",
        "deadline",
        "dimensions",
        "asset_links",
    ],
    output_keys=["clarified", "clarification_notes"],
    nullable_output_keys=["clarification_notes"],
    system_prompt=CLARIFY_SYSTEM_PROMPT,
    tools=[],
)

load_balance_node = NodeSpec(
    id="load_balance",
    name="Load Balance",
    description="Find designer with fewest active tasks for assignment",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["request_type", "project_name", "description", "deadline"],
    output_keys=[
        "assigned_designer_id",
        "assigned_designer_name",
        "designer_task_count",
        "assignment_rationale",
    ],
    nullable_output_keys=[],
    system_prompt=LOAD_BALANCE_SYSTEM_PROMPT,
    tools=[
        "monday_get_users",
        "monday_get_teams",
        "monday_search_items",
        "monday_list_boards",
    ],
)

create_task_node = NodeSpec(
    id="create_task",
    name="Create Task",
    description="Create Monday.com item and assign to selected designer",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=[
        "request_type",
        "project_name",
        "description",
        "deadline",
        "dimensions",
        "asset_links",
        "assigned_designer_id",
        "clarification_notes",
    ],
    output_keys=["monday_item_id", "monday_item_url", "task_created"],
    nullable_output_keys=["clarification_notes"],
    system_prompt=CREATE_TASK_SYSTEM_PROMPT,
    tools=[
        "monday_create_item",
        "monday_update_item",
        "monday_create_update",
        "monday_get_columns",
    ],
)

confirm_node = NodeSpec(
    id="confirm",
    name="Confirm",
    description="Present confirmation and ask for next action",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=[
        "request_type",
        "project_name",
        "deadline",
        "assigned_designer_name",
        "monday_item_url",
        "task_created",
    ],
    output_keys=["next_action"],
    nullable_output_keys=[],
    system_prompt=CONFIRM_SYSTEM_PROMPT,
    tools=[],
)

__all__ = [
    "intake_node",
    "clarify_node",
    "load_balance_node",
    "create_task_node",
    "confirm_node",
]
