"""Baserow credential specification."""

from __future__ import annotations

from .base import CredentialSpec

BASEROW_CREDENTIALS = {
    "baserow": CredentialSpec(
        env_var="BASEROW_TOKEN",
        tools=[
            "baserow_list_rows",
            "baserow_get_row",
            "baserow_create_row",
            "baserow_update_row",
            "baserow_delete_row",
        ],
        required=True,
        direct_api_key_supported=True,
        api_key_instructions="Create a database token in your Baserow User Settings > Database tokens.",
    ),
    "baserow_url": CredentialSpec(
        env_var="BASEROW_URL",
        required=False,
        direct_api_key_supported=True,
        api_key_instructions="Optional: Custom Baserow API URL (defaults to https://api.baserow.io).",
    ),
}
