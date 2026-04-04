"""
Zoho Books credentials.

Contains credentials for Zoho Books module management.
"""

from .base import CredentialSpec

ZOHO_BOOKS_CREDENTIALS = {
    "zoho_books": CredentialSpec(
        env_var="ZOHO_BOOKS_ORGANIZATION_ID",
        tools=[
            "zoho_books_get_contact",
            "zoho_books_list_invoices",
            "zoho_books_create_invoice",
        ],
        required=True,
        startup_required=False,
        help_url="https://www.zoho.com/books/api/v3/",
        description="OAuth2 credentials and Organization ID for the Zoho Books API",
        aden_supported=True,
        aden_provider_name="zoho_crm",
        direct_api_key_supported=False,
        api_key_instructions="""Zoho Books uses OAuth2 (not API keys). To get credentials:

1. Go to https://api-console.zoho.com/
2. Create a "Self Client" or "Server-based Application"
3. Select the required Zoho Books scopes (ZohoBooks.contacts.READ, etc.)
4. Copy the Client ID, Client Secret, and generate the initial Refresh Token.
5. Log into Zoho Books, go to Settings -> Organization Profile to copy your Organization ID.
6. Set environment variables:
   - ZOHO_CLIENT_ID=your_client_id
   - ZOHO_CLIENT_SECRET=your_client_secret
   - ZOHO_REFRESH_TOKEN=your_refresh_token
   - ZOHO_BOOKS_ORGANIZATION_ID=your_organization_id
   - ZOHO_REGION=in (valid: in, us, eu, au, jp, uk, sg — exact codes only).""",
        health_check_endpoint="https://www.zohoapis.com/books/v3/organizations",
        health_check_method="GET",
        credential_id="zoho_books",
        credential_key="access_token",
        credential_group="zoho_crm",
    ),
}
