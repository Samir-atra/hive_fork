from .agent import GitLabAssistantAgent, default_agent, goal, nodes, edges
from .config import metadata, default_config
from .nodes import (
    intake_node,
    list_projects_node,
    manage_issues_node,
    manage_mr_node,
    manage_pipelines_node,
    respond_node,
)

try:
    from .graph import gitlab_graph  # optional import for builder exposure
except Exception:
    gitlab_graph = None  # type: ignore

__all__ = [
    "GitLabAssistantAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "metadata",
    "default_config",
    "intake_node",
    "list_projects_node",
    "manage_issues_node",
    "manage_mr_node",
    "manage_pipelines_node",
    "respond_node",
    "gitlab_graph",
]
