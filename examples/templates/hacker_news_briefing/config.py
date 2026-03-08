"""Runtime configuration for Hacker News Briefing agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Hacker News Briefing"
    version: str = "1.0.0"
    description: str = (
        "Collects top Hacker News stories daily, ranks them by relevance, "
        "and delivers a concise briefing with 'why it matters' notes and source links. "
        "Supports configurable delivery channels (markdown, email, slack) and schedule."
    )
    intro_message: str = (
        "Hi! I'm your Hacker News briefing agent. I'll collect the top stories "
        "from Hacker News, rank them by relevance, and deliver a concise summary. "
        "Let's start by setting up your preferences."
    )


metadata = AgentMetadata()
