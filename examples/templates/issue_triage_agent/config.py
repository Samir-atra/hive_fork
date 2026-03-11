"""Runtime configuration for Issue Triage Agent."""

import json
from dataclasses import dataclass, field
from pathlib import Path


def _load_preferred_model() -> str:
    """Load preferred model from ~/.hive/configuration.json."""
    config_path = Path.home() / ".hive" / "configuration.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            llm = config.get("llm", {})
            if llm.get("provider") and llm.get("model"):
                return f"{llm['provider']}/{llm['model']}"
        except Exception:
            pass
    return "anthropic/claude-sonnet-4-20250514"


@dataclass
class RuntimeConfig:
    model: str = field(default_factory=_load_preferred_model)
    temperature: float = 0.3
    max_tokens: int = 40000
    api_key: str | None = None
    api_base: str | None = None


default_config = RuntimeConfig()


@dataclass
class AgentMetadata:
    name: str = "Issue Triage Agent"
    version: str = "1.0.0"
    description: str = (
        "Cross-channel issue triage agent that ingests signals from GitHub Issues, "
        "Discord channels, and Gmail, normalizes and deduplicates reports, assigns "
        "category/severity/confidence with rationale, and produces actionable triage reports."
    )
    intro_message: str = (
        "Hi! I'm your Issue Triage Agent. I'll help you triage incoming issues from "
        "GitHub, Discord, and Gmail. Tell me which channels to monitor and any specific "
        "filters (e.g., 'GitHub repo: owner/repo, Discord channel: #bugs, Gmail: support@')."
    )
    github_repo: str = ""
    discord_channel_id: str = ""
    gmail_query: str = "is:unread"


metadata = AgentMetadata()
