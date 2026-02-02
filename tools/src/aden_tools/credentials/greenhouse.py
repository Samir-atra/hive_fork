"""Credentials for Greenhouse integration."""

from .base import CredentialSpec

GREENHOUSE_CREDENTIALS = {
    "greenhouse_api_key": CredentialSpec(
        env_var="GREENHOUSE_API_KEY",
        description="Greenhouse Harvest API Key for recruiting automation",
        required=False,  # Optional unless Greenhouse tools are used
        tools=[
            "greenhouse_list_jobs",
            "greenhouse_get_job",
            "greenhouse_list_candidates",
            "greenhouse_get_candidate",
            "greenhouse_add_candidate",
            "greenhouse_list_applications",
        ],
        help_url="https://developers.greenhouse.io/harvest.html",
        api_key_instructions="""\
1. Log in to your Greenhouse account at https://app.greenhouse.io
2. Navigate to Configure > Dev Center > API Credential Management
3. Click 'Create New API Key'
4. Select 'Harvest API' as the API type
5. Give the key a descriptive name (e.g., 'Aden Integration')
6. Select the appropriate permissions:
   - Jobs: Read access (for listing/viewing jobs)
   - Candidates: Read/Write access (for listing/adding candidates)
   - Applications: Read access (for listing applications)
7. Click 'Create' and copy the generated API key
8. Set the environment variable: export GREENHOUSE_API_KEY=your_key""",
        health_check_endpoint="/jobs",
        credential_id="greenhouse",
        credential_key="api_key",
    ),
}

