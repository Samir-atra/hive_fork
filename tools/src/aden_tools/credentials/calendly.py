"""
Calendly credentials.
"""

from .base import CredentialSpec

CALENDLY_CREDENTIALS = {
    "calendly_api_key": CredentialSpec(
        env_var="CALENDLY_API_KEY",
        tools=["calendly_list_event_types", "calendly_create_scheduling_link"],
        node_types=[],
        required=False,
        startup_required=False,
        help_url="https://calendly.com/integrations/api_webhooks",
        description="Personal Access Token for Calendly API",
    ),
}
