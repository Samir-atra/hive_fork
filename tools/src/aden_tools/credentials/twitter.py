"""
Twitter tool credentials.

Contains credentials for Twitter API integration.
"""

from .base import CredentialSpec

TWITTER_CREDENTIALS = {
    "twitter": CredentialSpec(
        env_var="TWITTER_API_BEARER_TOKEN",
        tools=[
            "twitter_search_recent",
            "twitter_get_tweet",
            "twitter_get_user_profile"
        ],
        required=True,
        startup_required=False,
        help_url="https://developer.x.com/en/portal/dashboard",
        description="Twitter API V2 Bearer Token",
        # Auth method support
        aden_supported=False,
        direct_api_key_supported=True,
        api_key_instructions="""To get a Twitter Bearer Token:
1. Go to the Twitter Developer Portal (https://developer.x.com/en/portal/dashboard)
2. Create a Project and an App within that project.
3. Generate the Keys and Tokens for your App.
4. Copy the "Bearer Token".""",
        # Health check configuration
        health_check_endpoint="https://api.twitter.com/2/users/by/username/X",
        health_check_method="GET",
        # Credential store mapping
        credential_id="twitter",
        credential_key="bearer_token",
    ),
}
