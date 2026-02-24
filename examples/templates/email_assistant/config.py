"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()

@dataclass
class AgentMetadata:
    name: str = "Email Assistant"
    version: str = "1.0.0"
    description: str = (
        "End-to-end email assistant that categorizes intent, drafts replies, and executes workflows."
    )
    intro_message: str = (
        "Hi! I'm your email assistant. I'll fetch your emails, categorize them, "
        "and help you draft and send replies based on intent workflows."
    )

metadata = AgentMetadata()
