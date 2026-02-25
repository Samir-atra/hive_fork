from core.framework.graph.node import NodeSpec
from core.framework.graph.edge import GraphSpec, EdgeSpec, EdgeCondition

# Node definitions (mirror of six-node design)
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
    max_node_visits=0,
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
    max_node_visits=0,
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
    max_node_visits=0,
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
    max_node_visits=0,
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
)

# Edges (flow)
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
    # Error branches to respond for any failure
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

# Graph spec export
gitlab_graph = GraphSpec(
    id="gitlab-assistant-graph",
    goal_id="gitlab-001",
    entry_node="intake",
    terminal_nodes=[],  # forever-alive
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
