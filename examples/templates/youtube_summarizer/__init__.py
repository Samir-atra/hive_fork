"""
YouTube Summarizer Agent Template.

This template provides an agent that takes a YouTube URL,
fetches its transcript, and generates a structured summary
including a TL;DW, key takeaways, and a social media draft.
"""

from .agent import YouTubeSummarizerAgent, default_agent, goal, nodes, edges
from .config import RuntimeConfig, AgentMetadata, default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "YouTubeSummarizerAgent",
    "default_agent",
    "goal",
    "nodes",
    "edges",
    "RuntimeConfig",
    "AgentMetadata",
    "default_config",
    "metadata",
]
