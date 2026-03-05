"""Knowledge Agent - A RAG-based question answering agent."""

from .config import default_config, metadata, Config
from .agent import KnowledgeAgent, default_agent

__version__ = metadata.version
__all__ = [
    "KnowledgeAgent",
    "default_agent",
    "default_config",
    "metadata",
    "Config",
]
