"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "University Admin Navigation Agent"
    version: str = "1.0.0"
    description: str = (
        "Navigate institutional portals to find transcript request forms, "
        "student opportunities, administrative processes, and other resources."
    )
    intro_message: str = (
        "Hi! I'm your University Admin Navigation Agent. I can help you find transcript "
        "request forms, locate student jobs or ambassador roles, and figure out administrative "
        "processes like room bookings. How can I help you today?"
    )


metadata = AgentMetadata()
