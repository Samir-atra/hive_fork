"""Tests for HashiCorp Vault storage adapter.

All tests use mocked hvac.Client - no real Vault server required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType
from framework.credentials.vault.hashicorp import HashiCorpVaultStorage


class TestHashiCorpVaultStorage:
    @pytest.fixture
    def mock_hvac(self):
        """Mock hvac.Client for Vault testing."""
        with patch("framework.credentials.vault.hashicorp.hvac") as mock:
            client = MagicMock()
            client.is_authenticated.return_value = True
            mock.Client.return_value = client
            yield client

    def test_init_requires_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Vault token required"):
                HashiCorpVaultStorage(url="https://vault.example.com:8200")

    def test_init_auth_failure(self, mock_hvac):
        mock_hvac.is_authenticated.return_value = False
        with pytest.raises(ValueError, match="authentication failed"):
            HashiCorpVaultStorage(
                url="https://vault.example.com:8200",
                token="invalid-token",
            )

    def test_save_credential(self, mock_hvac):
        storage = HashiCorpVaultStorage(
            url="https://vault.example.com:8200",
            token="hvs.xxx",
        )
        cred = CredentialObject(
            id="my_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret"))},
        )
        storage.save(cred)
        mock_hvac.secrets.kv.v2.create_or_update_secret.assert_called_once()

    def test_load_credential_not_found(self, mock_hvac):
        mock_hvac.secrets.kv.v2.read_secret_version.side_effect = Exception("404 not found")
        storage = HashiCorpVaultStorage(
            url="https://vault.example.com:8200",
            token="hvs.xxx",
        )
        result = storage.load("nonexistent")
        assert result is None

    def test_delete_credential(self, mock_hvac):
        storage = HashiCorpVaultStorage(
            url="https://vault.example.com:8200",
            token="hvs.xxx",
        )
        result = storage.delete("my_api")
        assert result is True
        mock_hvac.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()
