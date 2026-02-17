"""
PagerDuty credential specifications.
"""

from .base import CredentialSpec

PAGERDUTY_CREDENTIALS = {
    "pagerduty": CredentialSpec(
        env_var="PAGERDUTY_API_KEY",
        description="PagerDuty REST API Key",
        help_url="https://support.pagerduty.com/docs/api-access-keys",
        required=True,
        tools=[
            "pagerduty_trigger_incident",
            "pagerduty_acknowledge_incident",
            "pagerduty_resolve_incident",
            "pagerduty_get_incident",
            "pagerduty_list_incidents",
            "pagerduty_add_incident_note",
        ],
    ),
    "pagerduty_email": CredentialSpec(
        env_var="PAGERDUTY_USER_EMAIL",
        description="PagerDuty User Email (used for the 'From' header in some API calls)",
        required=False,
    ),
}
