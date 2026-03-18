"""Tests for Azure Key Vault storage adapter."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from framework.credentials.azure.key_vault import AzureKeyVaultStorage
from framework.credentials.models import CredentialKey, CredentialObject, CredentialType


class TestAzureKeyVaultStorage:
    @pytest.fixture
    def mock_azure(self):
        """Mock azure-identity and urllib for testing."""
        with patch.dict("sys.modules", {"azure": MagicMock(), "azure.identity": MagicMock()}) as sys_modules:
            mock_cred = sys_modules["azure.identity"].DefaultAzureCredential
            credential_instance = MagicMock()
            mock_token = MagicMock()
            mock_token.token = "fake-token"
            credential_instance.get_token.return_value = mock_token
            mock_cred.return_value = credential_instance
            yield credential_instance

    def test_init_requires_azure_identity(self):
        with patch.dict("sys.modules", {"azure.identity": None}):
            with pytest.raises(ImportError, match="azure-identity"):
                AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")

    def test_secret_name_construction(self, mock_azure):
        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/", secret_prefix="hive")
        assert storage._secret_name("api_key") == "hive-api-key"

    def test_secret_name_sanitizes_paths(self, mock_azure):
        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert "path-with-slashes" in storage._secret_name("path/with/slashes")

    @patch("urllib.request.urlopen")
    def test_save_creates_or_updates_secret(self, mock_urlopen, mock_azure):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        cred = CredentialObject(
            id="test_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret"))},
        )

        storage.save(cred)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.method == "PUT"
        assert "hive-credentials-test-api" in req.full_url

    @patch("urllib.request.urlopen")
    def test_load_returns_credential(self, mock_urlopen, mock_azure):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "value": json.dumps({"_type": "api_key", "keys": {"api_key": {"name": "api_key", "value": "my-secret"}}, "id": "test_api"})
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        cred = storage.load("test_api")

        assert cred is not None
        assert cred.id == "test_api"
        assert cred.keys["api_key"].get_secret_value() == "my-secret"

    @patch("urllib.request.urlopen")
    def test_load_returns_none_for_missing(self, mock_urlopen, mock_azure):
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = error

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.load("nonexistent") is None

    @patch("urllib.request.urlopen")
    def test_delete_returns_true_on_success(self, mock_urlopen, mock_azure):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.delete("test_api") is True

    @patch("urllib.request.urlopen")
    def test_delete_returns_false_for_missing(self, mock_urlopen, mock_azure):
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = error

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.delete("nonexistent") is False

    @patch("urllib.request.urlopen")
    def test_list_all_with_pagination(self, mock_urlopen, mock_azure):
        mock_response1 = MagicMock()
        mock_response1.read.return_value = json.dumps({
            "value": [{"id": "https://test.vault.azure.net/secrets/hive-credentials-api1"}],
            "nextLink": "https://test.vault.azure.net/secrets?page=2"
        }).encode("utf-8")
        mock_response1.__enter__.return_value = mock_response1

        mock_response2 = MagicMock()
        mock_response2.read.return_value = json.dumps({
            "value": [{"id": "https://test.vault.azure.net/secrets/hive-credentials-api2"}],
            "nextLink": None
        }).encode("utf-8")
        mock_response2.__enter__.return_value = mock_response2

        mock_urlopen.side_effect = [mock_response1, mock_response2]

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        creds = storage.list_all()

        assert creds == ["api1", "api2"]

    @patch("urllib.request.urlopen")
    def test_exists_returns_true(self, mock_urlopen, mock_azure):
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.exists("test_api") is True

    @patch("urllib.request.urlopen")
    def test_exists_returns_false_for_missing(self, mock_urlopen, mock_azure):
        error = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = error

        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.exists("nonexistent") is False

    def test_health_check_success(self, mock_azure):
        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.health_check() is True

    def test_health_check_failure(self, mock_azure):
        mock_azure.get_token.side_effect = Exception("Failed")
        storage = AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")
        assert storage.health_check() is False
