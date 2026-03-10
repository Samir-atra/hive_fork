"""Runtime configuration for HR Onboarding Orchestrator."""

import json
from dataclasses import dataclass, field
from pathlib import Path


def _load_preferred_model() -> str:
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
class HROnboardingConfig:
    model: str = field(default_factory=_load_preferred_model)
    temperature: float = 0.3
    max_tokens: int = 16000
    api_key: str | None = None
    api_base: str | None = None
    polling_interval_minutes: int = 30
    escalation_timeout_hours: int = 48
    docusign_account_id: str | None = None
    monday_it_board_id: str = "IT_REQ"
    monday_finance_board_id: str = "FINANCE_ONBOARDING"
    slack_recruiter_channel: str = "#recruiting"


default_config = HROnboardingConfig()


@dataclass
class AgentMetadata:
    name: str = "HR Onboarding Orchestrator"
    version: str = "1.0.0"
    description: str = (
        "Automates the 'Offer to Day 1' journey by monitoring DocuSign offer "
        "letter signing, creating IT/Facilities/Finance tasks in Monday.com, "
        "sending welcome emails, and escalating to recruiters via Slack if needed."
    )
    intro_message: str = (
        "Welcome! I'm the HR Onboarding Orchestrator. I'll help automate "
        "the onboarding process from offer letter to Day 1. Please provide "
        "the new hire's details to begin."
    )


metadata = AgentMetadata()
