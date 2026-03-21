from __future__ import annotations

from aden_tools.credentials.base import CredentialSpec

OPENAPI_REST_CREDENTIALS = {
    "openapi_rest": CredentialSpec(
        env_var="OPENAPI_API_KEY",
        tools=["openapi_request"],
        description="API Key or Bearer Token for generic OpenAPI / REST integration",
        help_url="Depends on the target service API",
        api_key_instructions=(
            "Create an API key or personal access token from your service's developer console."
        ),
        direct_api_key_supported=True,
        aden_supported=False,
        health_check_endpoint="",  # User-defined health check not easily represented globally here
        health_check_method="GET",
        credential_id="openapi_rest",
        credential_key="api_key",  # or access_token / bearer_token
        credential_group="",
    ),
}
