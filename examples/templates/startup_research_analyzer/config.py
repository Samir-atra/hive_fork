"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Startup Research Analyzer"
    version: str = "1.0.0"
    description: str = (
        "Analyzes startups and businesses to extract funding, competitors, risks, "
        "and market size, providing an investor-style summary."
    )
    intro_message: str = (
        "Hi! I'm your startup research assistant. Provide me with a startup name or "
        "website URL and I'll analyze it to provide a comprehensive breakdown of its "
        "business, funding, competitors, risks, and market opportunity."
    )


metadata = AgentMetadata()
