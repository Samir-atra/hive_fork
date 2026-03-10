"""Runtime configuration for Content Research Swarm."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Content Research Swarm"
    version: str = "1.0.0"
    description: str = (
        "Multi-agent content pipeline that researches topics, drafts content, "
        "and edits for clarity. Demonstrates sequential agent orchestration "
        "with shared context passing between specialized agents."
    )
    intro_message: str = (
        "Hi! I'm your content research swarm. Tell me a topic and I'll research it, "
        "draft a Twitter thread or blog post, and polish it for publication. "
        "What topic would you like content for?"
    )


metadata = AgentMetadata()
