"""HashiCorp Vault storage adapter."""

from __future__ import annotations

import os

import hvac
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType
from framework.credentials.storage import CredentialStorage


class HashiCorpVaultStorage(CredentialStorage):
    """Storage adapter for HashiCorp Vault.

    Uses KV v2 secrets engine to store credentials.
    """

    def __init__(self, url: str, token: str | None = None, mount_point: str = "secret") -> None:
        """Initialize the Vault storage.

        Args:
            url: URL of the Vault server.
            token: Vault token. If not provided, reads from VAULT_TOKEN env var.
            mount_point: Mount point of the KV v2 secrets engine.

        Raises:
            ValueError: If token missing or authentication fails.
        """
        self.url = url
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.mount_point = mount_point

        if not self.token:
            raise ValueError("Vault token required")

        self.client = hvac.Client(url=self.url, token=self.token)

        if not self.client.is_authenticated():
            raise ValueError("authentication failed")

    def save(self, credential: CredentialObject) -> None:
        """Save a credential to Vault."""
        # Convert SecretStr to actual strings for storage
        secret_data = {
            "credential_type": credential.credential_type.value,
        }
        for key_name, cred_key in credential.keys.items():
            secret_data[key_name] = cred_key.get_secret_value()
            if cred_key.expires_at:
                secret_data[f"{key_name}_expires_at"] = cred_key.expires_at.isoformat()

        self.client.secrets.kv.v2.create_or_update_secret(
            path=credential.id,
            secret=secret_data,
            mount_point=self.mount_point,
        )

    def load(self, credential_id: str) -> CredentialObject | None:
        """Load a credential from Vault."""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=credential_id,
                mount_point=self.mount_point,
            )
            data = response["data"]["data"]
        except Exception:
            return None

        cred_type = CredentialType(data.pop("credential_type", CredentialType.CUSTOM.value))

        keys = {}
        for k, v in data.items():
            if not k.endswith("_expires_at"):
                keys[k] = CredentialKey(name=k, value=SecretStr(v))

        return CredentialObject(
            id=credential_id,
            credential_type=cred_type,
            keys=keys,
        )

    def delete(self, credential_id: str) -> bool:
        """Delete a credential from Vault."""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=credential_id,
                mount_point=self.mount_point,
            )
            return True
        except Exception:
            return False

    def list_all(self) -> list[str]:
        """List all credential IDs in Vault."""
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path="",
                mount_point=self.mount_point,
            )
            return response["data"]["keys"]
        except Exception:
            return []

    def exists(self, credential_id: str) -> bool:
        """Check if a credential exists in Vault."""
        return self.load(credential_id) is not None
