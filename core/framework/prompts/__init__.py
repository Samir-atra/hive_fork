"""
LLM System Prompts for Dynamic Agent Generation.

This module provides schema documentation and system prompts that enable LLMs
to generate valid agent.json definitions for the Hive framework.

The prompts address the ~90% failure rate issue when LLMs try to generate
agents without proper schema guidance.

Usage:
    from framework.prompts import (
        AGENT_JSON_SCHEMA,
        AGENT_GENERATION_SYSTEM_PROMPT,
        AGENT_GENERATION_COMPACT_PROMPT,
    )

    # Use in agent builder tools
    system_prompt = AGENT_GENERATION_SYSTEM_PROMPT
"""

from framework.prompts.agent_schema import (
    AGENT_GENERATION_COMPACT_PROMPT,
    AGENT_GENERATION_SYSTEM_PROMPT,
    AGENT_JSON_SCHEMA,
)

__all__ = [
    "AGENT_JSON_SCHEMA",
    "AGENT_GENERATION_SYSTEM_PROMPT",
    "AGENT_GENERATION_COMPACT_PROMPT",
]
