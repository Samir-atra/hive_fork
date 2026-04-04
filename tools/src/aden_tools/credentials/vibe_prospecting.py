"""
VibeProspecting credentials.

Contains credentials for the VibeProspecting API.
Requires VIBE_API_KEY.
"""

from .base import CredentialSpec

VIBE_PROSPECTING_CREDENTIALS = {
    "vibe_api_key": CredentialSpec(
        env_var="VIBE_API_KEY",
        tools=[
            "search_prospects_vibe",
            "generate_lead_list_vibe",
        ],
        required=True,
        startup_required=False,
        help_url="https://vibeprospecting.com/docs",
        description="VibeProspecting API key for prospect discovery and lead lists",
        direct_api_key_supported=True,
        api_key_instructions="""To set up VibeProspecting API access:
1. Go to your VibeProspecting dashboard
2. Navigate to Account Settings > API
3. Set environment variable:
   export VIBE_API_KEY=vd_live_your_key""",
        health_check_endpoint="https://api.vibeprospecting.com/v1/prospects/search?limit=1",
        credential_id="vibe_api_key",
        credential_key="api_key",
    ),
}
