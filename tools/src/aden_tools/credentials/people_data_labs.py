"""
People Data Labs credentials.

Contains credentials for the People Data Labs API.
Requires PDL_API_KEY.
"""

from .base import CredentialSpec

PEOPLE_DATA_LABS_CREDENTIALS = {
    "pdl_api_key": CredentialSpec(
        env_var="PDL_API_KEY",
        tools=[
            "enrich_person_pdl",
            "enrich_company_pdl",
            "search_persons_pdl",
            "search_companies_pdl",
        ],
        required=True,
        startup_required=False,
        help_url="https://docs.peopledatalabs.com/",
        description="People Data Labs API key for data enrichment and search",
        direct_api_key_supported=True,
        api_key_instructions="""To set up People Data Labs API access:
1. Go to your People Data Labs dashboard
2. Navigate to API settings to get your API key
3. Set environment variable:
   export PDL_API_KEY=your-api-key""",
        health_check_endpoint="https://api.peopledatalabs.com/v5/company/enrich?website=peopledatalabs.com",
        credential_id="pdl_api_key",
        credential_key="api_key",
    ),
}
