"""
Datadog Agent - Data Integrity Monitoring Agent.

Audits data quality, detects NULL values and schema mismatches,
quarantines invalid records, and validates ETL processes.
"""

from .agent import (
    DatadogAgent,
    conversation_mode,
    default_agent,
    edges,
    entry_node,
    entry_points,
    goal,
    identity_prompt,
    loop_config,
    nodes,
    pause_nodes,
    terminal_nodes,
)
from .config import default_config, metadata

__version__ = "1.0.0"

__all__ = [
    "DatadogAgent",
    "conversation_mode",
    "default_agent",
    "default_config",
    "edges",
    "entry_node",
    "entry_points",
    "goal",
    "identity_prompt",
    "loop_config",
    "metadata",
    "nodes",
    "pause_nodes",
    "terminal_nodes",
]
