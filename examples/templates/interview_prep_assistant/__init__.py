"""
Interview Preparation Assistant Agent.

Detect interview-related emails, extract key details (role, company, date),
generate interview questions and preparation tips, and provide ATS-based
resume optimization suggestions.
"""

from .agent import (
    InterviewPrepAssistant,
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
from .config import AgentMetadata, RuntimeConfig, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "InterviewPrepAssistant",
    "default_agent",
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
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
