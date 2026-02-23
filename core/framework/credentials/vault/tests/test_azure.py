"""
Unit tests for AzureKeyVaultStorage.

Uses mocking to avoid requiring actual Azure credentials or Key Vault access.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import SecretStr

from core.framework.credentials import (
    CredentialKey,
    CredentialObject,
    CredentialType,
)
from core.framework.credentials.vault.azure import AzureKeyVaultStorage


class MockSecretProperties:
    """Mock for Azure SecretProperties."""

    def __init__(
        self,
        name: str,
        id: str,
        created_on: datetime | None = None,
        updated_on: datetime | None = None,
        expires_on: datetime | None = None,
        enabled: bool = True,
        content_type: str | None = None,
    ):
        self.name = name
        self.id = id
        self.created_on = created_on
        self.updated_on = updated_on
        self.expires_on = expires_on
        self.enabled = enabled
        self.content_type = content_type


class MockSecret:
    """Mock for Azure KeyVaultSecret."""

    def __init__(
        self,
        name: str,
        value: str,
        properties: MockSecretProperties | None = None,
    ):
        self.name = name
        self.value = value
        self.properties = properties or MockSecretProperties(
            name=name, id=f"https://vault.vault.azure.net/secrets/{name}/version123"
        )


class MockDeleteSecretPoller:
    """Mock for LROPoller returned by begin_delete_secret."""

    def __init__(self):
        self._done = False

    def wait(self):
        self._done = True

    def done(self):
        return self._done


class MockRecoverPoller:
    """Mock for LROPoller returned by begin_recover_deleted_secret."""

    def __init__(self):
        self._done = False

    def wait(self):
        self._done = True


class TestAzureKeyVaultStorageInit:
    """Tests for AzureKeyVaultStorage initialization."""

    def test_init_with_vault_url(self):
        """Test initialization with explicit vault URL."""
        mock_client = MagicMock()

        with patch("core.framework.credentials.vault.azure.SecretClient", return_value=mock_client):
            with patch("core.framework.credentials.vault.azure.DefaultAzureCredential"):
                storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

        assert storage._vault_url == "https://my-vault.vault.azure.net"
        assert storage._secret_prefix == "hive-credentials"

    def test_init_with_vault_name(self):
        """Test initialization with vault name (constructs URL)."""
        mock_client = MagicMock()

        with patch("core.framework.credentials.vault.azure.SecretClient", return_value=mock_client):
            with patch("core.framework.credentials.vault.azure.DefaultAzureCredential"):
                storage = AzureKeyVaultStorage(vault_name="my-vault")

        assert storage._vault_url == "https://my-vault.vault.azure.net"

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("AZURE_KEY_VAULT_URL", "https://env-vault.vault.azure.net")

        mock_client = MagicMock()

        with patch("core.framework.credentials.vault.azure.SecretClient", return_value=mock_client):
            with patch("core.framework.credentials.vault.azure.DefaultAzureCredential"):
                storage = AzureKeyVaultStorage()

        assert storage._vault_url == "https://env-vault.vault.azure.net"

    def test_init_without_url_raises(self):
        """Test that initialization without URL raises ValueError."""
        with patch("core.framework.credentials.vault.azure.DefaultAzureCredential"):
            with pytest.raises(ValueError, match="Key Vault URL required"):
                AzureKeyVaultStorage()

    def test_init_with_custom_prefix(self):
        """Test initialization with custom secret prefix."""
        mock_client = MagicMock()

        with patch("core.framework.credentials.vault.azure.SecretClient", return_value=mock_client):
            with patch("core.framework.credentials.vault.azure.DefaultAzureCredential"):
                storage = AzureKeyVaultStorage(
                    vault_url="https://my-vault.vault.azure.net",
                    secret_prefix="custom-prefix",
                )

        assert storage._secret_prefix == "custom-prefix"

    def test_init_with_custom_credential(self):
        """Test initialization with custom Azure credential."""
        mock_client = MagicMock()
        mock_credential = MagicMock()

        with patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=mock_client
        ) as mock_sc:
            storage = AzureKeyVaultStorage(
                vault_url="https://my-vault.vault.azure.net",
                credential=mock_credential,
            )

        # Verify SecretClient was called with the custom credential
        mock_sc.assert_called_once()
        assert mock_sc.call_args[1]["credential"] == mock_credential

    def test_init_without_azure_packages_raises(self):
        """Test that missing Azure packages raises ImportError."""
        with patch.dict("sys.modules", {"azure.identity": None, "azure.keyvault.secrets": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError, match="azure-identity"):
                    AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")


class TestAzureKeyVaultStorageSecretName:
    """Tests for secret name generation."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_simple_credential_id(self):
        """Test simple credential ID conversion."""
        assert self.storage._secret_name("my_api") == "hive-credentials-my-api"

    def test_credential_id_with_underscores(self):
        """Test credential ID with underscores gets converted to dashes."""
        assert self.storage._secret_name("my_super_api") == "hive-credentials-my-super-api"

    def test_credential_id_with_slashes(self):
        """Test credential ID with slashes gets converted to dashes."""
        assert self.storage._secret_name("my/api/key") == "hive-credentials-my-api-key"

    def test_credential_id_with_special_chars(self):
        """Test credential ID with special characters gets sanitized."""
        assert self.storage._secret_name("my@api#key") == "hive-credentials-myapikey"

    def test_credential_id_with_consecutive_dashes(self):
        """Test consecutive dashes are removed."""
        assert self.storage._secret_name("my__api") == "hive-credentials-my-api"


class TestAzureKeyVaultStorageSave:
    """Tests for saving credentials."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_save_simple_credential(self):
        """Test saving a simple API key credential."""
        cred = CredentialObject(
            id="test_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("test-key-value"))},
        )

        self.storage.save(cred)

        self.mock_client.set_secret.assert_called_once()
        call_args = self.mock_client.set_secret.call_args
        assert call_args[0][0] == "hive-credentials-test-api"

        # Verify the JSON structure
        data = json.loads(call_args[0][1])
        assert data["_type"] == "api_key"
        assert data["api_key"] == "test-key-value"

    def test_save_oauth2_credential(self):
        """Test saving an OAuth2 credential with multiple keys."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        cred = CredentialObject(
            id="github_oauth",
            credential_type=CredentialType.OAUTH2,
            keys={
                "access_token": CredentialKey(
                    name="access_token", value=SecretStr("ghp_xxx"), expires_at=expires
                ),
                "refresh_token": CredentialKey(name="refresh_token", value=SecretStr("ghr_xxx")),
            },
            provider_id="oauth2",
            description="GitHub OAuth",
            auto_refresh=True,
        )

        self.storage.save(cred)

        call_args = self.mock_client.set_secret.call_args
        data = json.loads(call_args[0][1])

        assert data["_type"] == "oauth2"
        assert data["access_token"] == "ghp_xxx"
        assert data["refresh_token"] == "ghr_xxx"
        assert data["_provider_id"] == "oauth2"
        assert data["_description"] == "GitHub OAuth"
        assert data["_auto_refresh"] == "true"
        assert "_expires_access_token" in data

    def test_save_with_metadata(self):
        """Test saving a credential with key metadata."""
        cred = CredentialObject(
            id="test_api",
            keys={
                "api_key": CredentialKey(
                    name="api_key",
                    value=SecretStr("test-key"),
                    metadata={"client_id": "abc", "scope": "read"},
                )
            },
        )

        self.storage.save(cred)

        call_args = self.mock_client.set_secret.call_args
        data = json.loads(call_args[0][1])
        assert "_metadata_api_key" in data


class TestAzureKeyVaultStorageLoad:
    """Tests for loading credentials."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_load_simple_credential(self):
        """Test loading a simple credential."""
        secret_value = json.dumps(
            {
                "_type": "api_key",
                "api_key": "test-key-value",
            }
        )
        self.mock_client.get_secret.return_value = MockSecret(
            "hive-credentials-test-api", secret_value
        )

        cred = self.storage.load("test_api")

        assert cred is not None
        assert cred.id == "test_api"
        assert cred.credential_type == CredentialType.API_KEY
        assert cred.get_key("api_key") == "test-key-value"

    def test_load_oauth2_credential(self):
        """Test loading an OAuth2 credential with expiration."""
        expires_str = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        secret_value = json.dumps(
            {
                "_type": "oauth2",
                "access_token": "ghp_xxx",
                "refresh_token": "ghr_xxx",
                "_expires_access_token": expires_str,
                "_provider_id": "oauth2",
            }
        )
        self.mock_client.get_secret.return_value = MockSecret(
            "hive-credentials-github-oauth", secret_value
        )

        cred = self.storage.load("github_oauth")

        assert cred is not None
        assert cred.credential_type == CredentialType.OAUTH2
        assert cred.get_key("access_token") == "ghp_xxx"
        assert cred.get_key("refresh_token") == "ghr_xxx"
        assert cred.provider_id == "oauth2"
        assert cred.keys["access_token"].expires_at is not None

    def test_load_nonexistent_credential(self):
        """Test loading a credential that doesn't exist."""
        from azure.core.exceptions import ResourceNotFoundError

        self.mock_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")

        cred = self.storage.load("nonexistent")

        assert cred is None

    def test_load_with_404_error(self):
        """Test loading returns None on 404 error."""
        error = Exception("404 Not Found")
        self.mock_client.get_secret.side_effect = error

        cred = self.storage.load("nonexistent")

        assert cred is None


class TestAzureKeyVaultStorageDelete:
    """Tests for deleting credentials."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_delete_existing_credential(self):
        """Test deleting an existing credential."""
        self.mock_client.begin_delete_secret.return_value = MockDeleteSecretPoller()

        result = self.storage.delete("test_api")

        assert result is True
        self.mock_client.begin_delete_secret.assert_called_once_with("hive-credentials-test-api")

    def test_delete_nonexistent_credential(self):
        """Test deleting a credential that doesn't exist."""
        from azure.core.exceptions import ResourceNotFoundError

        self.mock_client.begin_delete_secret.side_effect = ResourceNotFoundError("Not found")

        result = self.storage.delete("nonexistent")

        assert result is False


class TestAzureKeyVaultStorageListAll:
    """Tests for listing credentials."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_list_all_credentials(self):
        """Test listing all credentials."""
        mock_secrets = [
            MockSecretProperties(name="hive-credentials-api-one", id="id1"),
            MockSecretProperties(name="hive-credentials-api-two", id="id2"),
            MockSecretProperties(name="hive-credentials-api-three", id="id3"),
            MockSecretProperties(name="other-prefix-secret", id="id4"),  # Should be excluded
        ]
        self.mock_client.list_properties_of_secrets.return_value = mock_secrets

        result = self.storage.list_all()

        assert "api-one" in result
        assert "api-two" in result
        assert "api-three" in result
        assert "other-prefix-secret" not in result

    def test_list_all_empty(self):
        """Test listing when no credentials exist."""
        self.mock_client.list_properties_of_secrets.return_value = []

        result = self.storage.list_all()

        assert result == []


class TestAzureKeyVaultStorageExists:
    """Tests for checking credential existence."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_exists_true(self):
        """Test exists returns True for existing credential."""
        self.mock_client.get_secret.return_value = MockSecret(
            "hive-credentials-test-api", '{"_type": "api_key"}'
        )

        result = self.storage.exists("test_api")

        assert result is True

    def test_exists_false(self):
        """Test exists returns False for nonexistent credential."""
        from azure.core.exceptions import ResourceNotFoundError

        self.mock_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        result = self.storage.exists("nonexistent")

        assert result is False


class TestAzureKeyVaultStorageSpecificOperations:
    """Tests for Azure Key Vault-specific operations."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_get_secret_metadata(self):
        """Test getting secret metadata."""
        created = datetime.now(UTC) - timedelta(days=1)
        updated = datetime.now(UTC)

        props = MockSecretProperties(
            name="hive-credentials-test-api",
            id="https://vault.vault.azure.net/secrets/hive-credentials-test-api/version123",
            created_on=created,
            updated_on=updated,
            enabled=True,
            content_type="application/json",
        )
        secret = MockSecret("hive-credentials-test-api", '{"_type": "api_key"}', props)
        self.mock_client.get_secret.return_value = secret

        metadata = self.storage.get_secret_metadata("test_api")

        assert metadata is not None
        assert metadata["name"] == "hive-credentials-test-api"
        assert metadata["version"] == "version123"
        assert metadata["enabled"] is True

    def test_get_secret_metadata_not_found(self):
        """Test getting metadata for nonexistent secret."""
        from azure.core.exceptions import ResourceNotFoundError

        self.mock_client.get_secret.side_effect = ResourceNotFoundError("Not found")

        metadata = self.storage.get_secret_metadata("nonexistent")

        assert metadata is None

    def test_load_version(self):
        """Test loading a specific version of a credential."""
        secret_value = json.dumps(
            {
                "_type": "api_key",
                "api_key": "versioned-key",
            }
        )
        self.mock_client.get_secret.return_value = MockSecret(
            "hive-credentials-test-api", secret_value
        )

        cred = self.storage.load_version("test_api", "version123")

        assert cred is not None
        assert cred.get_key("api_key") == "versioned-key"
        self.mock_client.get_secret.assert_called_once_with(
            "hive-credentials-test-api", version="version123"
        )

    def test_list_versions(self):
        """Test listing all versions of a credential."""
        created1 = datetime.now(UTC) - timedelta(days=2)
        created2 = datetime.now(UTC) - timedelta(days=1)

        mock_versions = [
            MockSecretProperties(
                name="hive-credentials-test-api",
                id="https://vault.vault.azure.net/secrets/hive-credentials-test-api/v2",
                created_on=created2,
                enabled=True,
            ),
            MockSecretProperties(
                name="hive-credentials-test-api",
                id="https://vault.vault.azure.net/secrets/hive-credentials-test-api/v1",
                created_on=created1,
                enabled=False,
            ),
        ]
        self.mock_client.list_properties_of_secret_versions.return_value = mock_versions

        versions = self.storage.list_versions("test_api")

        assert len(versions) == 2
        assert versions[0]["version"] == "v2"
        assert versions[0]["enabled"] is True
        assert versions[1]["version"] == "v1"
        assert versions[1]["enabled"] is False

    def test_purge_deleted(self):
        """Test purging a soft-deleted credential."""
        self.mock_client.purge_deleted_secret.return_value = None

        result = self.storage.purge_deleted("test_api")

        assert result is True
        self.mock_client.purge_deleted_secret.assert_called_once_with("hive-credentials-test-api")

    def test_recover_deleted(self):
        """Test recovering a soft-deleted credential."""
        self.mock_client.begin_recover_deleted_secret.return_value = MockRecoverPoller()

        result = self.storage.recover_deleted("test_api")

        assert result is True
        self.mock_client.begin_recover_deleted_secret.assert_called_once_with(
            "hive-credentials-test-api"
        )


class TestAzureKeyVaultStorageRoundTrip:
    """Tests for full save/load round trips."""

    def setup_method(self):
        """Set up storage for each test."""
        self.mock_client = MagicMock()
        self.stored_secrets: dict[str, str] = {}

        def mock_set_secret(name: str, value: str):
            self.stored_secrets[name] = value

        def mock_get_secret(name: str, version: str | None = None):
            if name in self.stored_secrets:
                return MockSecret(name, self.stored_secrets[name])
            from azure.core.exceptions import ResourceNotFoundError

            raise ResourceNotFoundError("Not found")

        self.mock_client.set_secret.side_effect = mock_set_secret
        self.mock_client.get_secret.side_effect = mock_get_secret

        self.patcher1 = patch(
            "core.framework.credentials.vault.azure.SecretClient", return_value=self.mock_client
        )
        self.patcher2 = patch("core.framework.credentials.vault.azure.DefaultAzureCredential")
        self.patcher1.start()
        self.patcher2.start()
        self.storage = AzureKeyVaultStorage(vault_url="https://my-vault.vault.azure.net")

    def teardown_method(self):
        """Clean up patches."""
        self.patcher1.stop()
        self.patcher2.stop()

    def test_roundtrip_api_key(self):
        """Test save and load roundtrip for API key credential."""
        original = CredentialObject(
            id="test_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret-key-value"))},
            description="Test API Key",
        )

        self.storage.save(original)
        loaded = self.storage.load("test_api")

        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.credential_type == original.credential_type
        assert loaded.get_key("api_key") == "secret-key-value"
        assert loaded.description == "Test API Key"

    def test_roundtrip_oauth2_with_expiration(self):
        """Test save and load roundtrip for OAuth2 with expiration."""
        expires = datetime.now(UTC) + timedelta(hours=1)

        original = CredentialObject(
            id="oauth_credential",
            credential_type=CredentialType.OAUTH2,
            keys={
                "access_token": CredentialKey(
                    name="access_token",
                    value=SecretStr("access-token-value"),
                    expires_at=expires,
                    metadata={"scope": "read write"},
                ),
                "refresh_token": CredentialKey(
                    name="refresh_token", value=SecretStr("refresh-token-value")
                ),
            },
            provider_id="oauth2",
            auto_refresh=True,
        )

        self.storage.save(original)
        loaded = self.storage.load("oauth_credential")

        assert loaded is not None
        assert loaded.credential_type == CredentialType.OAUTH2
        assert loaded.get_key("access_token") == "access-token-value"
        assert loaded.get_key("refresh_token") == "refresh-token-value"
        assert loaded.provider_id == "oauth2"
        assert loaded.auto_refresh is True
        # Check expiration was preserved (compare ISO format since microseconds might differ)
        assert loaded.keys["access_token"].expires_at is not None
        assert (
            loaded.keys["access_token"].expires_at.isoformat().startswith(expires.isoformat()[:19])
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
