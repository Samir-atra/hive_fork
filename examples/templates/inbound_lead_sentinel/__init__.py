"""Inbound Lead Sentinel agent template.

Automatically enriches, scores, and routes inbound demo requests.
"""

from .agent import InboundLeadSentinel, default_agent
from .config import default_config, metadata

__all__ = ["default_agent", "default_config", "metadata", "InboundLeadSentinel"]
