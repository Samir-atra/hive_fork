"""HR Onboarding Orchestrator - Automates the "Offer to Day 1" journey.

This agent orchestrates the complete onboarding workflow:
- Monitor DocuSign offer letter signing status
- Create IT/Facilities/Finance tasks in Monday.com when signed
- Send welcome email to new hire
- Escalate to recruiter via Slack if not signed in 48h
"""

from .agent import HROnboardingOrchestrator, default_agent
from .config import default_config, metadata

__all__ = [
    "HROnboardingOrchestrator",
    "default_agent",
    "default_config",
    "metadata",
]
