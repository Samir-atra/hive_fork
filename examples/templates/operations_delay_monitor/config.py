"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Operations Delay Monitor"
    version: str = "1.0.0"
    description: str = (
        "Monitors scheduled tasks. If a task's ETA exceeds the planned schedule threshold, "
        "it checks traffic and weather conditions, generates a short explanation for the delay, "
        "and notifies stakeholders with an updated ETA."
    )
    intro_message: str = "I am ready to monitor operations. Please provide task inputs."


metadata = AgentMetadata()
