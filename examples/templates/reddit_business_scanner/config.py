"""Runtime configuration."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Reddit Business Opportunity Scanner"
    version: str = "1.0.0"
    description: str = "Monitors specific subreddits for business opportunities and drafts tailored outreach."
    intro_message: str = "I'm ready to scan Reddit for business opportunities. What subreddits should I check?"


@dataclass
class ScannerConfig:
    subreddits: list[str]
    keywords: list[str]
    score_threshold: int = 7
    outreach_tone: str = "helpful"


# Default fallback config
default_scanner_config = ScannerConfig(
    subreddits=["SaaS", "entrepreneur", "smallbusiness", "startups"],
    keywords=["looking for", "frustrated with", "does anyone know", "pain point"],
    score_threshold=7,
    outreach_tone="helpful",
)

metadata = AgentMetadata()
