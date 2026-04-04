"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()

@dataclass
class AgentMetadata:
    name: str = "YouTube Summarizer Agent"
    version: str = "1.0.0"
    description: str = (
        "Takes a YouTube URL, fetches its transcript, and generates a structured Markdown summary "
        "including a TL;DW, key technical takeaways, and a social media draft."
    )
    intro_message: str = (
        "Hi! Provide a YouTube URL, and I'll generate a comprehensive structured summary "
        "including a TL;DW, key takeaways, and a social media draft."
    )

metadata = AgentMetadata()
