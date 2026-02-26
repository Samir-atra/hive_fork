from framework.graph.node import NodeSpec
from framework.graph.edge import GraphSpec, EdgeSpec, EdgeCondition

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
You are the intake node for the GitLab Assistant.

Your job is to understand what the user wants to do and set the task_request output.

**STEP 1 — Greet and understand:**
- If this is a new conversation, greet the user and ask what they'd like to do
- Listen to their request (list projects, manage issues, view MRs, trigger pipelines)

**STEP 2 — Set the task_request:**
Once you understand the user's intent, call set_output with a task_request:
- action: "list_projects" | "list_issues" | "create_issue" | "get_mr" | "trigger_pipeline"
- details: any relevant parameters the user mentioned

Example:
set_output("task_request", {"action": "list_projects", "owned": true})

DO NOT call GitLab tools yourself. Just gather the request and pass it to the next node.
""",
)

list_projects_node = NodeSpec(
    id="list_projects",
    name="List Projects",
    description="Search/list available GitLab projects",
    node_type="event_loop",
    input_keys=["task_request"],
    output_keys=["projects"],
    tools=["gitlab_list_projects"],
    client_facing=False,
    max_node_visits=3,
    system_prompt="""\
You are the List Projects node for GitLab Assistant.

**Your task:**
Execute the user's project listing request using gitlab_list_projects.

**Available tool:**
- gitlab_list_projects(search="optional", owned=true/false, limit=20)

**Instructions:**
1. Read the task_request from memory to understand parameters
2. Call gitlab_list_projects with appropriate parameters
3. Call set_output("projects", {...}) with the results

**STEP 1 — Call the tool:**
gitlab_list_projects(search="...", owned=true/false)

**STEP 2 — Set output:**
set_output("projects", {"items": [...], "count": N})

Always set the "projects" output even if the result is empty or an error occurred.
""",
)

manage_issues_node = NodeSpec(
    id="manage_issues",
    name="Manage Issues",
    description="Handle issue operations (list, create)",
    node_type="event_loop",
    input_keys=["projects", "task_request"],
    output_keys=["issues", "created_issue", "error"],
    tools=["gitlab_list_issues", "gitlab_create_issue"],
    client_facing=False,
    max_node_visits=3,
    system_prompt="""\
You are the Manage Issues node for GitLab Assistant.

**Your task:**
Handle issue-related requests (list or create issues).

**Available tools:**
- gitlab_list_issues(project_id, state="opened", labels="...", limit=20)
- gitlab_create_issue(project_id, title, description, labels)

**Instructions:**
1. Read task_request to determine the action
2. Use projects from memory if project_id is needed
3. Execute the appropriate tool
4. Set all required outputs: issues, created_issue, error

**For listing issues:**
- gitlab_list_issues(project_id="123", state="opened")

**For creating issues:**
- gitlab_create_issue(project_id="123", title="...", description="...")

**Set outputs:**
- set_output("issues", {...}) - list results
- set_output("created_issue", {...}) - creation result
- set_output("error", null) - or error message if failed

Always set all three outputs.
""",
)

manage_mr_node = NodeSpec(
    id="manage_mr",
    name="Manage Merge Requests",
    description="Handle merge request operations",
    node_type="event_loop",
    input_keys=["projects", "task_request"],
    output_keys=["merge_request", "error"],
    tools=["gitlab_get_merge_request"],
    client_facing=False,
    max_node_visits=3,
    system_prompt="""\
You are the Manage Merge Requests node for GitLab Assistant.

**Your task:**
Handle merge request queries.

**Available tool:**
- gitlab_get_merge_request(project_id, mr_iid)

**Instructions:**
1. Read task_request for MR details (project_id, mr_iid)
2. Call gitlab_get_merge_request if requested
3. Set outputs: merge_request, error

**Example:**
gitlab_get_merge_request(project_id="123", mr_iid=5)

**Set outputs:**
- set_output("merge_request", {...}) - MR details
- set_output("error", null) - or error message

If the user didn't request MR info, set empty values and proceed.
""",
)

manage_pipelines_node = NodeSpec(
    id="manage_pipelines",
    name="Manage Pipelines",
    description="Handle pipeline operations",
    node_type="event_loop",
    input_keys=["projects", "task_request"],
    output_keys=["pipeline", "error"],
    tools=["gitlab_trigger_pipeline"],
    client_facing=False,
    max_node_visits=3,
    system_prompt="""\
You are the Manage Pipelines node for GitLab Assistant.

**Your task:**
Handle CI/CD pipeline operations.

**Available tool:**
- gitlab_trigger_pipeline(project_id, ref)

**Instructions:**
1. Read task_request for pipeline details (project_id, branch/ref)
2. Call gitlab_trigger_pipeline if requested
3. Set outputs: pipeline, error

**Example:**
gitlab_trigger_pipeline(project_id="123", ref="main")

**Set outputs:**
- set_output("pipeline", {...}) - pipeline details
- set_output("error", null) - or error message

If the user didn't request pipeline operations, set empty values and proceed.
""",
)

respond_node = NodeSpec(
    id="respond",
    name="Respond",
    description="Present results to user",
    node_type="event_loop",
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
    client_facing=True,
    max_node_visits=1,
    system_prompt="""\
You are the Respond node for GitLab Assistant.

**Your task:**
Present the results of the user's request in a clear, friendly format.

**Available memory:**
- task_request: what the user asked for
- projects: project listing results
- issues: issue listing/creation results
- merge_request: MR details
- pipeline: pipeline trigger results
- error: any errors that occurred

**Instructions:**
1. Review all available outputs from previous nodes
2. Format the results nicely for the user
3. If there were errors, explain what went wrong
4. Ask if the user needs anything else

**STEP 1 — Summarize results:**
Present what was accomplished or found.

**STEP 2 — Set outputs:**
set_output("response", "Your results summary...")
set_output("done", true)

Be concise and helpful. The conversation will continue with the intake node.
""",
)

edges = [
    EdgeSpec(
        id="intake-to-list-projects",
        source="intake",
        target="list_projects",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="list-projects-to-manage-issues",
        source="list_projects",
        target="manage_issues",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="manage-issues-to-manage-mr",
        source="manage_issues",
        target="manage_mr",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="manage-mr-to-manage-pipelines",
        source="manage_mr",
        target="manage_pipelines",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="manage-pipelines-to-respond",
        source="manage_pipelines",
        target="respond",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="respond-to-intake",
        source="respond",
        target="intake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="intake-to-respond-error",
        source="intake",
        target="respond",
        condition=EdgeCondition.ON_FAILURE,
        priority=-1,
    ),
    EdgeSpec(
        id="list-projects-to-respond-error",
        source="list_projects",
        target="respond",
        condition=EdgeCondition.ON_FAILURE,
        priority=-1,
    ),
    EdgeSpec(
        id="manage-issues-to-respond-error",
        source="manage_issues",
        target="respond",
        condition=EdgeCondition.ON_FAILURE,
        priority=-1,
    ),
    EdgeSpec(
        id="manage-mr-to-respond-error",
        source="manage_mr",
        target="respond",
        condition=EdgeCondition.ON_FAILURE,
        priority=-1,
    ),
    EdgeSpec(
        id="manage-pipelines-to-respond-error",
        source="manage_pipelines",
        target="respond",
        condition=EdgeCondition.ON_FAILURE,
        priority=-1,
    ),
]

gitlab_graph = GraphSpec(
    id="gitlab-assistant-graph",
    goal_id="gitlab-001",
    entry_node="intake",
    terminal_nodes=[],
    nodes=[
        intake_node,
        list_projects_node,
        manage_issues_node,
        manage_mr_node,
        manage_pipelines_node,
        respond_node,
    ],
    edges=edges,
)

__all__ = ["gitlab_graph"]
