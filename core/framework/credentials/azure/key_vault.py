"""Azure Key Vault storage backend."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import SecretStr

from framework.credentials.models import (
    CredentialDecryptionError,
    CredentialObject,
)
from framework.credentials.storage import CredentialStorage

logger = logging.getLogger(__name__)

class AzureKeyVaultStorage(CredentialStorage):
    """
    Azure Key Vault storage backend.

    Stores credentials as JSON strings in Azure Key Vault.
    Uses azure-identity to authenticate and REST API to communicate with Azure.

    Example:
        storage = AzureKeyVaultStorage(
            vault_url="https://my-vault.vault.azure.net/",
            secret_prefix="hive-credentials"
        )
    """

    def __init__(
        self,
        vault_url: str,
        secret_prefix: str = "hive-credentials"
    ):
        """
        Initialize Azure Key Vault storage.

        Args:
            vault_url: URL of the Azure Key Vault (e.g. 'https://my-vault.vault.azure.net/')
            secret_prefix: Prefix for secret names. Azure Key Vault secrets must match
                           ^[0-9a-zA-Z-]+$, so this is combined with the credential ID using dashes.
        """
        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as e:
            raise ImportError(
                "Azure Key Vault support requires 'azure-identity'. "
                "Install with: uv pip install azure-identity"
            ) from e

        if not vault_url.endswith("/"):
            vault_url += "/"

        self.vault_url = vault_url
        self.secret_prefix = secret_prefix.strip("-")

        self._credential = DefaultAzureCredential()
        self._api_version = "7.4"

    def _get_token(self) -> str:
        """Get an OAuth token for Key Vault."""
        return self._credential.get_token("https://vault.azure.net/.default").token

    def _secret_name(self, credential_id: str) -> str:
        """
        Construct the full secret name.

        Azure Key Vault secrets must be alphanumeric and dashes only.
        """
        # Replace invalid characters with dashes
        import re
        safe_id = re.sub(r"[^0-9a-zA-Z-]+", "-", credential_id)
        if self.secret_prefix:
            return f"{self.secret_prefix}-{safe_id}"
        return safe_id

    def _serialize_credential(self, credential: CredentialObject) -> str:
        """Convert credential to a JSON string for storage."""
        data = credential.model_dump(mode="json")

        for key_name, key_data in data.get("keys", {}).items():
            if "value" in key_data:
                actual_key = credential.keys.get(key_name)
                if actual_key:
                    key_data["value"] = actual_key.get_secret_value()

        data["_type"] = credential.credential_type.value

        return json.dumps(data)

    def _deserialize_credential(self, data: dict[str, Any]) -> CredentialObject:
        """Reconstruct credential from dictionary."""
        if "keys" not in data and "id" not in data:
            raise ValueError("Secret does not match expected CredentialObject schema")

        for key_data in data.get("keys", {}).values():
            if "value" in key_data and isinstance(key_data["value"], str):
                key_data["value"] = SecretStr(key_data["value"])

        data.pop("_type", None)

        return CredentialObject.model_validate(data)

    def save(self, credential: CredentialObject) -> None:
        """Save a credential to Azure Key Vault."""
        import urllib.error
        import urllib.request

        secret_name = self._secret_name(credential.id)
        secret_string = self._serialize_credential(credential)

        url = f"{self.vault_url}secrets/{secret_name}?api-version={self._api_version}"

        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json"
        }

        data = json.dumps({"value": secret_string}).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")

        try:
            with urllib.request.urlopen(req) as response:
                if response.status not in (200, 201):
                    raise Exception(f"Failed to save credential: {response.read().decode('utf-8')}")
            logger.debug(f"Saved credential '{credential.id}' to Azure Key Vault")
        except urllib.error.HTTPError as e:
            logger.error(f"Failed to save credential '{credential.id}': {e.read().decode('utf-8')}")
            raise

    def load(self, credential_id: str) -> CredentialObject | None:
        """Load a credential from Azure Key Vault."""
        import urllib.error
        import urllib.request

        secret_name = self._secret_name(credential_id)
        url = f"{self.vault_url}secrets/{secret_name}?api-version={self._api_version}"

        headers = {
            "Authorization": f"Bearer {self._get_token()}"
        }

        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req) as response:
                body = json.loads(response.read().decode("utf-8"))
                secret_value = body.get("value")

                if not secret_value:
                    raise CredentialDecryptionError("Secret value is empty")

                data = json.loads(secret_value)
                if "id" not in data:
                    data["id"] = credential_id
                return self._deserialize_credential(data)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            logger.error(f"Failed to load credential '{credential_id}': {e.read().decode('utf-8')}")
            raise
        except Exception as e:
            raise CredentialDecryptionError(
                f"Failed to parse credential '{credential_id}': {e}"
            ) from e

    def delete(self, credential_id: str) -> bool:
        """Delete a credential from Azure Key Vault."""
        import urllib.error
        import urllib.request

        secret_name = self._secret_name(credential_id)
        url = f"{self.vault_url}secrets/{secret_name}?api-version={self._api_version}"

        headers = {
            "Authorization": f"Bearer {self._get_token()}"
        }

        req = urllib.request.Request(url, headers=headers, method="DELETE")

        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    logger.debug(f"Deleted credential '{credential_id}' from Azure Key Vault")
                    return True
                return False
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            err_msg = e.read().decode("utf-8")
            logger.error(f"Failed to delete credential '{credential_id}': {err_msg}")
            raise

    def list_all(self) -> list[str]:
        """List all credential IDs in Azure Key Vault."""
        import urllib.error
        import urllib.request

        url = f"{self.vault_url}secrets?api-version={self._api_version}"

        headers = {
            "Authorization": f"Bearer {self._get_token()}"
        }

        credential_ids = []

        while url:
            req = urllib.request.Request(url, headers=headers, method="GET")

            try:
                with urllib.request.urlopen(req) as response:
                    body = json.loads(response.read().decode("utf-8"))

                    for item in body.get("value", []):
                        # Extract name from id URL (e.g. https://vault.vault.azure.net/secrets/name)
                        secret_id_url = item.get("id", "")
                        name = secret_id_url.split("/")[-1]

                        if self.secret_prefix and name.startswith(f"{self.secret_prefix}-"):
                            credential_ids.append(name[len(f"{self.secret_prefix}-"):])
                        elif not self.secret_prefix:
                            credential_ids.append(name)

                    url = body.get("nextLink")
            except urllib.error.HTTPError as e:
                logger.error(f"Failed to list credentials: {e.read().decode('utf-8')}")
                raise

        return credential_ids

    def exists(self, credential_id: str) -> bool:
        """Check if a credential exists in Azure Key Vault."""
        import urllib.error
        import urllib.request

        secret_name = self._secret_name(credential_id)
        # Using the same GET request as exists since Azure KV doesn't have a HEAD or lean describe endpoint
        # that doesn't return the value for secrets specifically, but getting metadata works by getting the secret without value?
        # Actually, GET on the secret returns the value. We can just catch 404.
        url = f"{self.vault_url}secrets/{secret_name}?api-version={self._api_version}"

        headers = {
            "Authorization": f"Bearer {self._get_token()}"
        }

        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

    def health_check(self) -> bool:
        """Check if Azure credentials are valid."""
        try:
            self._get_token()
            return True
        except Exception:
            return False
