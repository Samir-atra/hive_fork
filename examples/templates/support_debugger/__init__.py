"""
Support Debugger Agent - Cyclic investigation workflow for support debugging.

Diagnoses issues through hypothesis formation, evidence gathering, and
confidence refinement. Demonstrates conditional loop termination with
max_node_visits safety bounds.
"""

from .agent import SupportDebuggerAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "SupportDebuggerAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
