"""Node specs for GitLab Assistant agent."""

from framework.graph import NodeSpec

# Node 1: intake
intake_node = NodeSpec(
    id="intake",
    name="GitLab Intake",
    description="Gather what the user wants to do with GitLab automation",
    node_type="event_loop",
    input_keys=[],
    output_keys=["task_request"],
    tools=[],
    client_facing=True,
    max_node_visits=1,
    system_prompt="""\
You are a GitLab intake specialist. Gather the user's GitLab automation goals.

**STEP 1 — Read (text only, NO tool calls):**
- Collect the user's intent for GitLab operations (projects, issues, MRs, pipelines).
- If unclear, ask 1 clarifying question.
- If clear, summarize and ask for confirmation including the actions to perform.

**STEP 2 — After confirmation, call set_output:**
- set_output("task_request", "<structured GitLab request payload>")
""",
)

# Node 2: list_projects
list_projects_node = NodeSpec(
    id="list_projects",
    name="List Projects",
    description="Search/list available projects",
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["task_request"],
    output_keys=["projects"],
    tools=["gitlab_list_projects"],
    client_facing=False,
    system_prompt="""\
You are a GitLab tool executor. Given a task_request, list and filter projects.
""",
)

# Node 3: manage_issues
manage_issues_node = NodeSpec(
    id="manage_issues",
    name="Manage Issues",
    description="Handle issue operations (list, create)",
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["projects", "task_request"],
    output_keys=["issues", "created_issue", "error"],
    tools=["gitlab_list_issues", "gitlab_create_issue"],
    client_facing=False,
    system_prompt="""\
You manage issues for a given project. You can list issues or create new ones.
If creating, provide a title and optional description/labels.
""",
)

# Node 4: manage_mr
manage_mr_node = NodeSpec(
    id="manage_mr",
    name="Manage Merge Requests",
    description="Handle merge request operations",
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["projects", "task_request"],
    output_keys=["merge_request", "error"],
    tools=["gitlab_get_merge_request"],
    client_facing=False,
    system_prompt="""\
Fetch and present MR details as needed.
""",
)

# Node 5: manage_pipelines
manage_pipelines_node = NodeSpec(
    id="manage_pipelines",
    name="Manage Pipelines",
    description="Handle pipeline operations",
    node_type="event_loop",
    max_node_visits=0,
    input_keys=["projects", "task_request"],
    output_keys=["pipeline", "error"],
    tools=["gitlab_trigger_pipeline"],
    client_facing=False,
    system_prompt="""\
You trigger and monitor GitLab pipelines for a given project.
""",
)

# Node 6: respond
respond_node = NodeSpec(
    id="respond",
    name="Respond",
    description="Present results to user",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=1,
    input_keys=[
        "task_request",
        "projects",
        "issues",
        "merge_request",
        "pipeline",
        "error",
    ],
    output_keys=["done", "response"],
    tools=[],
    system_prompt="""\
Present the results to the user and indicate completion.
""",
)

__all__ = [
    "intake_node",
    "list_projects_node",
    "manage_issues_node",
    "manage_mr_node",
    "manage_pipelines_node",
    "respond_node",
]
