"""
Content Research Swarm - Multi-agent content pipeline.

Researches topics, drafts content, and edits for publication.
Demonstrates sequential agent orchestration with shared context passing.
"""

from .agent import ContentResearchSwarmAgent, default_agent, edges, goal, nodes
from .config import AgentMetadata, RuntimeConfig, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "ContentResearchSwarmAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
