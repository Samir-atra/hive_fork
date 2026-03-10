"""
Configuration for Business Process Executor Agent.
"""

from dataclasses import dataclass


@dataclass
class AgentMetadata:
    name: str = "Business Process Executor"
    version: str = "1.0.0"
    description: str = (
        "Autonomous business process agent that executes multi-step operations "
        "from a single goal statement. Outcome-driven with human-in-the-loop "
        "at decision boundaries only."
    )
    intro_message: str = (
        "Business Process Executor ready. Give me a business goal in plain English "
        "and I'll execute it end-to-end. I'll only ask for your input at critical "
        "decision points, then provide a clear summary of results."
    )


@dataclass
class RuntimeConfig:
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    temperature: float = 0.7
    api_key: str | None = None
    api_base: str | None = None

    max_execution_steps: int = 50
    decision_confidence_threshold: float = 0.75
    max_retries_per_step: int = 3
    escalation_keywords: tuple = (
        "cancel",
        "stop",
        "abort",
        "legal",
        "lawsuit",
        "urgent",
        "emergency",
        "security",
        "breach",
        "confidential",
    )


metadata = AgentMetadata()
default_config = RuntimeConfig()
