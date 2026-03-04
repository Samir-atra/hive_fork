"""
Vercel deployment and hosting credentials.

Contains credentials for Vercel deployment management integration.
"""

from .base import CredentialSpec

VERCEL_CREDENTIALS = {
    "vercel": CredentialSpec(
        env_var="VERCEL_AUTH_TOKEN",
        tools=[
            "vercel_create_deployment",
            "vercel_list_projects",
            "vercel_get_deployment_status",
            "vercel_set_env_variable",
        ],
        required=True,
        startup_required=False,
        help_url="https://vercel.com/account/tokens",
        description="Vercel Authentication Token for deployment management",
        aden_supported=False,
        aden_provider_name="",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Vercel Auth Token:
1. Log in to your Vercel account
2. Go to Account Settings (click your profile picture)
3. Select Tokens from the sidebar
4. Click Create to generate a new token
5. Give it a name (e.g., "Hive Agent") and choose the scope (usually "Full Access" or specific teams)
6. Copy the token""",
        health_check_endpoint="https://api.vercel.com/v2/user",
        health_check_method="GET",
        credential_id="vercel",
        credential_key="auth_token",
    ),
}
