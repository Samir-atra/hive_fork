"""Runtime configuration for Datadog Agent."""

from dataclasses import dataclass

from framework.config import RuntimeConfig


@dataclass
class AgentMetadata:
    name: str = "Datadog Agent"
    version: str = "1.0.0"
    description: str = (
        "Data integrity monitoring agent that audits data quality, "
        "detects NULL values and schema mismatches, quarantines invalid records, "
        "and validates ETL processes. Supports PostgreSQL, BigQuery, CSV, and Excel data sources."
    )
    intro_message: str = (
        "Welcome to Datadog Agent - your data integrity guardian. "
        "I can audit your data sources, detect quality issues like NULL values and schema mismatches, "
        "quarantine invalid records, and help ensure regulatory compliance. "
        "What data would you like me to analyze?"
    )


metadata = AgentMetadata()
default_config = RuntimeConfig(temperature=0.2)
