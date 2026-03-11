"""
Monday.com tool credentials.

Contains credentials for Monday.com work management platform integration.
"""

from .base import CredentialSpec

MONDAY_CREDENTIALS = {
    "monday": CredentialSpec(
        env_var="MONDAY_API_KEY",
        tools=[
            "monday_create_item",
            "monday_list_boards",
            "monday_search_items",
            "monday_update_item",
            "monday_get_item",
            "monday_delete_item",
            "monday_get_board_items",
            "monday_get_columns",
            "monday_create_update",
            "monday_get_updates",
            "monday_get_users",
            "monday_get_teams",
        ],
        required=True,
        startup_required=False,
        help_url="https://monday.com/developers/v2",
        description="Monday.com API Token (Personal or OAuth token)",
        aden_supported=True,
        aden_provider_name="monday",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Monday.com API Token:
1. Log in to your Monday.com account
2. Click on your avatar in the top right corner
3. Go to "Administration" > "API"
4. Click "Generate a new token" or copy an existing one
5. For OAuth2: Create an app in Monday.com Marketplace > Developers
6. Required scopes for full functionality:
   - boards:read, boards:write
   - items:read, items:write
   - users:read
   - teams:read
   - updates:read, updates:write""",
        health_check_endpoint="https://api.monday.com/v2",
        health_check_method="POST",
        credential_id="monday",
        credential_key="api_key",
    ),
}
