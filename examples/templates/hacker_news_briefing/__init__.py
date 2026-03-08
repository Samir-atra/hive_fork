"""
Hacker News Briefing - Daily HN briefing with configurable delivery.

Collects top Hacker News stories, ranks them by relevance, produces
a concise briefing with 'why it matters' notes, and delivers via
user-configurable channels (markdown, email, slack).
"""

from .agent import HackerNewsBriefingAgent, default_agent, edges, goal, nodes
from .config import AgentMetadata, RuntimeConfig, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "HackerNewsBriefingAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
