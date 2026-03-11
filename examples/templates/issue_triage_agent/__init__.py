"""Issue Triage Agent - Cross-channel issue triage for GitHub, Discord, and Gmail."""

from .agent import (
    IssueTriageAgent,
    conversation_mode,
    default_agent,
    edges,
    entry_node,
    entry_points,
    goal,
    identity_prompt,
    loop_config,
    nodes,
    pause_nodes,
    terminal_nodes,
)
from .config import default_config, metadata

__all__ = [
    "IssueTriageAgent",
    "default_agent",
    "default_config",
    "metadata",
    "goal",
    "nodes",
    "edges",
    "entry_node",
    "entry_points",
    "pause_nodes",
    "terminal_nodes",
    "conversation_mode",
    "identity_prompt",
    "loop_config",
]
