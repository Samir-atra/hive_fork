"""
Azure Key Vault storage adapter.

Provides integration with Azure Key Vault for enterprise secret management.
Requires the 'azure-identity' and 'azure-keyvault-secrets' packages:
    pip install azure-identity azure-keyvault-secrets
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from pydantic import SecretStr

from ..models import CredentialKey, CredentialObject, CredentialType
from ..storage import CredentialStorage

logger = logging.getLogger(__name__)


class AzureKeyVaultStorage(CredentialStorage):
    """
    Azure Key Vault storage adapter.

    Features:
    - Seamless authentication via DefaultAzureCredential (supports CLI, Managed Identity, etc.)
    - Secret versioning and soft-delete support
    - Audit logging via Azure Monitor
    - Works locally (via CLI login) and in production (via Managed Identity)

    The adapter stores credentials in Azure Key Vault with the following naming convention:
        {secret_prefix}-{credential_id}

    Each secret's value is stored as a JSON object containing:
        {
            "_type": "oauth2",
            "access_token": "xxx",
            "refresh_token": "yyy",
            "_expires_access_token": "2024-01-26T12:00:00",
            "_provider_id": "oauth2"
        }

    Example:
        storage = AzureKeyVaultStorage(
            vault_url="https://my-vault.vault.azure.net",
            secret_prefix="hive-credentials"
        )

        store = CredentialStore(storage=storage)

        # Credentials are now stored in Azure Key Vault
        store.save_credential(credential)
        credential = store.get_credential("my_api")

    Authentication:
        The adapter uses DefaultAzureCredential which supports multiple authentication methods:
        1. Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
        2. Managed Identity (when running in Azure)
        3. Azure CLI (az login)
        4. Visual Studio Code
        5. Interactive browser

        For production, Managed Identity is recommended:
        - No secrets to manage
        - Automatic credential rotation
        - Fine-grained access control via Azure RBAC

    Requirements:
        pip install azure-identity azure-keyvault-secrets

    Azure Setup:
        1. Create a Key Vault:
            az keyvault create --name my-vault --resource-group my-rg

        2. Grant your identity access:
            az keyvault set-policy --name my-vault --spn <your-client-id> \\
                --secret-permissions get set list delete

        3. For Managed Identity (recommended for production):
            # Create a user-assigned managed identity
            az identity create --name my-identity --resource-group my-rg

            # Grant the identity access to Key Vault
            az keyvault set-policy --name my-vault --object-id <identity-principal-id> \\
                --secret-permissions get set list delete
    """

    def __init__(
        self,
        vault_url: str | None = None,
        vault_name: str | None = None,
        secret_prefix: str = "hive-credentials",
        credential: Any = None,
    ):
        """
        Initialize Azure Key Vault storage.

        Args:
            vault_url: Full Key Vault URL (e.g., https://my-vault.vault.azure.net)
                       If not provided, reads from AZURE_KEY_VAULT_URL env var
            vault_name: Key Vault name (alternative to vault_url)
                        Will construct URL as https://{vault_name}.vault.azure.net
            secret_prefix: Prefix for all secrets in the vault (default: "hive-credentials")
            credential: Optional Azure credential object. If None, uses DefaultAzureCredential

        Raises:
            ImportError: If azure-identity or azure-keyvault-secrets is not installed
            ValueError: If vault URL cannot be determined
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError as e:
            raise ImportError(
                "Azure Key Vault support requires 'azure-identity' and 'azure-keyvault-secrets'. "
                "Install with: pip install azure-identity azure-keyvault-secrets"
            ) from e

        # Determine vault URL
        if vault_url:
            self._vault_url = vault_url
        elif vault_name:
            self._vault_url = f"https://{vault_name}.vault.azure.net"
        else:
            self._vault_url = os.environ.get("AZURE_KEY_VAULT_URL")

        if not self._vault_url:
            raise ValueError(
                "Key Vault URL required. Set AZURE_KEY_VAULT_URL env var, "
                "or pass vault_url/vault_name parameter."
            )

        self._secret_prefix = secret_prefix

        # Use provided credential or create default
        self._credential = credential or DefaultAzureCredential()

        # Create secret client
        self._client = SecretClient(
            vault_url=self._vault_url,
            credential=self._credential,
        )

        logger.info(f"Connected to Azure Key Vault at {self._vault_url}")

    def _secret_name(self, credential_id: str) -> str:
        """
        Build secret name for credential.

        Azure Key Vault secret names must be alphanumeric with dashes.
        """
        # Sanitize credential_id for Azure naming rules
        safe_id = credential_id.replace("_", "-").replace("/", "-").replace("\\", "-")
        # Remove any characters that aren't alphanumeric or dash
        safe_id = "".join(c for c in safe_id if c.isalnum() or c == "-")
        # Remove consecutive dashes and trim
        while "--" in safe_id:
            safe_id = safe_id.replace("--", "-")
        safe_id = safe_id.strip("-")

        return f"{self._secret_prefix}-{safe_id}"

    def save(self, credential: CredentialObject) -> None:
        """Save credential to Azure Key Vault."""
        import json

        secret_name = self._secret_name(credential.id)
        data = self._serialize_for_vault(credential)
        json_value = json.dumps(data, default=str)

        try:
            self._client.set_secret(secret_name, json_value)
            logger.debug(
                f"Saved credential '{credential.id}' to Azure Key Vault as '{secret_name}'"
            )
        except Exception as e:
            logger.error(f"Failed to save credential '{credential.id}' to Azure Key Vault: {e}")
            raise

    def load(self, credential_id: str) -> CredentialObject | None:
        """Load credential from Azure Key Vault."""
        import json

        secret_name = self._secret_name(credential_id)

        try:
            secret = self._client.get_secret(secret_name)
            data = json.loads(secret.value)
            return self._deserialize_from_vault(credential_id, data)
        except Exception as e:
            # Check if it's a "not found" error
            error_str = str(e).lower()
            if (
                "not found" in error_str
                or "404" in error_str
                or "secretnotfound" in error_str.lower()
            ):
                logger.debug(f"Credential '{credential_id}' not found in Azure Key Vault")
                return None
            logger.error(f"Failed to load credential '{credential_id}' from Azure Key Vault: {e}")
            raise

    def delete(self, credential_id: str) -> bool:
        """Delete credential from Azure Key Vault (soft delete)."""
        secret_name = self._secret_name(credential_id)

        try:
            poller = self._client.begin_delete_secret(secret_name)
            poller.wait()  # Wait for deletion to complete
            logger.debug(f"Deleted credential '{credential_id}' from Azure Key Vault")
            return True
        except Exception as e:
            error_str = str(e).lower()
            if (
                "not found" in error_str
                or "404" in error_str
                or "secretnotfound" in error_str.lower()
            ):
                return False
            logger.error(f"Failed to delete credential '{credential_id}' from Azure Key Vault: {e}")
            raise

    def list_all(self) -> list[str]:
        """
        List all credentials under the prefix.

        Note: This lists all secrets with the prefix and extracts credential IDs.
        """
        try:
            # Get all secrets and filter by prefix
            credential_ids = []
            secrets = self._client.list_properties_of_secrets()

            for secret_prop in secrets:
                name = secret_prop.name
                # Check if it starts with our prefix
                if name.startswith(f"{self._secret_prefix}-"):
                    # Extract credential ID (remove prefix)
                    cred_id = name[len(self._secret_prefix) + 1 :]
                    if cred_id:  # Avoid empty strings
                        credential_ids.append(cred_id)

            return credential_ids
        except Exception as e:
            logger.error(f"Failed to list credentials from Azure Key Vault: {e}")
            raise

    def exists(self, credential_id: str) -> bool:
        """Check if credential exists in Azure Key Vault."""
        try:
            secret_name = self._secret_name(credential_id)
            self._client.get_secret(secret_name)
            return True
        except Exception:
            return False

    def _serialize_for_vault(self, credential: CredentialObject) -> dict[str, Any]:
        """Convert credential to Azure Key Vault secret format."""
        data: dict[str, Any] = {
            "_type": credential.credential_type.value,
        }

        if credential.provider_id:
            data["_provider_id"] = credential.provider_id

        if credential.description:
            data["_description"] = credential.description

        if credential.auto_refresh:
            data["_auto_refresh"] = "true"

        for key_name, key in credential.keys.items():
            data[key_name] = key.get_secret_value()

            if key.expires_at:
                data[f"_expires_{key_name}"] = key.expires_at.isoformat()

            if key.metadata:
                data[f"_metadata_{key_name}"] = str(key.metadata)

        return data

    def _deserialize_from_vault(self, credential_id: str, data: dict[str, Any]) -> CredentialObject:
        """Reconstruct credential from Azure Key Vault secret."""
        # Extract metadata fields
        cred_type = CredentialType(data.pop("_type", "api_key"))
        provider_id = data.pop("_provider_id", None)
        description = data.pop("_description", "")
        auto_refresh = data.pop("_auto_refresh", "") == "true"

        # Build keys dict
        keys: dict[str, CredentialKey] = {}

        # Find all non-metadata keys
        key_names = [k for k in data.keys() if not k.startswith("_")]

        for key_name in key_names:
            value = data[key_name]

            # Check for expiration
            expires_at = None
            expires_key = f"_expires_{key_name}"
            if expires_key in data:
                try:
                    expires_at = datetime.fromisoformat(data[expires_key])
                except (ValueError, TypeError):
                    pass

            # Check for metadata
            metadata: dict[str, Any] = {}
            metadata_key = f"_metadata_{key_name}"
            if metadata_key in data:
                try:
                    import ast

                    metadata = ast.literal_eval(data[metadata_key])
                except (ValueError, SyntaxError):
                    pass

            keys[key_name] = CredentialKey(
                name=key_name,
                value=SecretStr(value),
                expires_at=expires_at,
                metadata=metadata,
            )

        return CredentialObject(
            id=credential_id,
            credential_type=cred_type,
            keys=keys,
            provider_id=provider_id,
            description=description,
            auto_refresh=auto_refresh,
        )

    # --- Azure Key Vault-Specific Operations ---

    def get_secret_metadata(self, credential_id: str) -> dict[str, Any] | None:
        """
        Get Azure Key Vault metadata for a secret (version, timestamps, etc.).

        Args:
            credential_id: The credential identifier

        Returns:
            Metadata dict or None if not found
        """
        secret_name = self._secret_name(credential_id)

        try:
            secret = self._client.get_secret(secret_name)
            return {
                "id": secret.id,
                "name": secret.name,
                "version": secret.id.split("/")[-1] if "/" in secret.id else None,
                "created_on": secret.properties.created_on.isoformat()
                if secret.properties.created_on
                else None,
                "updated_on": secret.properties.updated_on.isoformat()
                if secret.properties.updated_on
                else None,
                "expires_on": secret.properties.expires_on.isoformat()
                if secret.properties.expires_on
                else None,
                "content_type": secret.properties.content_type,
                "enabled": secret.properties.enabled,
            }
        except Exception:
            return None

    def load_version(self, credential_id: str, version: str) -> CredentialObject | None:
        """
        Load a specific version of a credential.

        Args:
            credential_id: The credential identifier
            version: Version identifier from Azure Key Vault

        Returns:
            CredentialObject or None
        """
        import json

        secret_name = self._secret_name(credential_id)

        try:
            secret = self._client.get_secret(secret_name, version=version)
            data = json.loads(secret.value)
            return self._deserialize_from_vault(credential_id, data)
        except Exception:
            return None

    def list_versions(self, credential_id: str) -> list[dict[str, Any]]:
        """
        List all versions of a credential.

        Args:
            credential_id: The credential identifier

        Returns:
            List of version metadata dicts
        """
        secret_name = self._secret_name(credential_id)

        try:
            versions = []
            for version_prop in self._client.list_properties_of_secret_versions(secret_name):
                versions.append(
                    {
                        "id": version_prop.id,
                        "version": version_prop.id.split("/")[-1]
                        if "/" in version_prop.id
                        else None,
                        "created_on": version_prop.created_on.isoformat()
                        if version_prop.created_on
                        else None,
                        "updated_on": version_prop.updated_on.isoformat()
                        if version_prop.updated_on
                        else None,
                        "expires_on": version_prop.expires_on.isoformat()
                        if version_prop.expires_on
                        else None,
                        "enabled": version_prop.enabled,
                    }
                )
            return versions
        except Exception as e:
            logger.error(f"Failed to list versions for '{credential_id}': {e}")
            return []

    def purge_deleted(self, credential_id: str) -> bool:
        """
        Permanently purge a soft-deleted credential.

        Note: This operation requires purge permission and is irreversible.

        Args:
            credential_id: The credential identifier

        Returns:
            True if successful
        """
        secret_name = self._secret_name(credential_id)

        try:
            self._client.purge_deleted_secret(secret_name)
            logger.debug(f"Purged deleted credential '{credential_id}' from Azure Key Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to purge deleted credential '{credential_id}': {e}")
            return False

    def recover_deleted(self, credential_id: str) -> bool:
        """
        Recover a soft-deleted credential.

        Args:
            credential_id: The credential identifier

        Returns:
            True if successful
        """
        secret_name = self._secret_name(credential_id)

        try:
            poller = self._client.begin_recover_deleted_secret(secret_name)
            poller.wait()
            logger.debug(f"Recovered deleted credential '{credential_id}' in Azure Key Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to recover deleted credential '{credential_id}': {e}")
            return False
