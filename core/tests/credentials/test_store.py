import logging
from datetime import UTC, datetime, timedelta

from pydantic import SecretStr

from framework.credentials.models import (
    CredentialKey,
    CredentialObject,
    CredentialType,
    CredentialUsageSpec,
)
from framework.credentials.provider import CredentialProvider


class MockProvider(CredentialProvider):
    """Mock provider to test refresh logic."""

    def __init__(self, provider_id="mock_provider"):
        self._provider_id = provider_id
        self.refresh_called = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    @property
    def supported_types(self) -> list[CredentialType]:
        return [CredentialType.OAUTH2]

    def refresh(self, credential: CredentialObject) -> CredentialObject:
        self.refresh_called += 1
        credential.set_key("access_token", f"refreshed-token-{self.refresh_called}")
        return credential

    def validate(self, credential: CredentialObject) -> bool:
        return True

    def should_refresh(self, credential: CredentialObject) -> bool:
        return credential.needs_refresh


def test_credential_store_crud(memory_store, sample_credential):
    # Save
    memory_store.save_credential(sample_credential)
    assert memory_store.exists("test_cred")

    # Get
    cred = memory_store.get_credential("test_cred")
    assert cred is not None
    assert cred.id == "test_cred"

    # Get Key
    key = memory_store.get_key("test_cred", "api_key")
    assert key == "test-key-123"

    # Legacy Get
    assert memory_store.get("test_cred") == "test-key-123"

    # Delete
    assert memory_store.delete_credential("test_cred") is True
    assert memory_store.exists("test_cred") is False


def test_credential_store_cache(memory_store, sample_credential):
    # Enable cache TTL
    memory_store._cache_ttl = 10  # 10 seconds

    # Save credential
    memory_store.save_credential(sample_credential)

    # Access should cache it
    _ = memory_store.get_credential("test_cred")
    assert "test_cred" in memory_store._cache

    # Modifying storage directly bypasses cache updating
    # Let's verify it reads from cache
    memory_store._storage.delete("test_cred")
    cached_cred = memory_store.get_credential("test_cred")
    assert cached_cred is not None

    # Clear cache
    memory_store.clear_cache()
    assert memory_store.get_credential("test_cred") is None


def test_credential_store_cache_ttl(memory_store, sample_credential):
    memory_store._cache_ttl = 0  # Immediate expiry
    memory_store.save_credential(sample_credential)

    # Modifying storage directly
    memory_store._storage.delete("test_cred")

    # Because TTL is 0, it should attempt to fetch from storage and return None
    assert memory_store.get_credential("test_cred") is None


def test_credential_store_refresh(memory_store, sample_oauth_credential):
    memory_store._auto_refresh = True
    provider = MockProvider()
    memory_store.register_provider(provider)

    # Set expiration in the past to trigger refresh
    past = datetime.now(UTC) - timedelta(days=1)
    sample_oauth_credential.keys["access_token"].expires_at = past
    sample_oauth_credential.provider_id = "mock_provider"

    memory_store.save_credential(sample_oauth_credential)

    # Access should trigger refresh
    cred = memory_store.get_credential("test_oauth")
    assert cred is not None
    assert provider.refresh_called == 1
    assert cred.get_key("access_token") == "refreshed-token-1"

    # Check manual refresh
    refreshed_manual = memory_store.refresh_credential("test_oauth")
    assert refreshed_manual is not None
    assert provider.refresh_called == 2
    assert refreshed_manual.get_key("access_token") == "refreshed-token-2"


def test_credential_store_validation(memory_store, sample_credential):
    memory_store.save_credential(sample_credential)

    spec = CredentialUsageSpec(credential_id="test_cred", required_keys=["api_key", "missing_key"])
    memory_store.register_usage(spec)

    # Validate usage
    errors = memory_store.validate_for_usage("test_cred")
    assert len(errors) == 1
    assert "Missing required key 'missing_key'" in errors[0]

    # Validate all
    all_errors = memory_store.validate_all()
    assert "test_cred" in all_errors
    assert len(all_errors["test_cred"]) == 1


def test_secret_str_not_in_logs(caplog):
    """Ensure SecretStr values are masked in log output."""
    caplog.set_level(logging.DEBUG)

    cred = CredentialObject(
        id="sensitive",
        keys={"password": CredentialKey(name="password", value=SecretStr("super-secret-12345"))},
    )

    # We will log the model dump to simulate what might happen in error handlers or debug logs
    logger = logging.getLogger("test_logger")
    logger.debug(f"Credential info: {cred.model_dump_json()}")

    # Verify the secret value doesn't appear in logs
    assert "super-secret-12345" not in caplog.text
    assert "**********" in caplog.text or "SecretStr" in caplog.text


def test_credential_store_resolve_for_usage(memory_store, sample_credential):
    memory_store.save_credential(sample_credential)

    spec = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"Authorization": "Bearer {{test_cred.api_key}}"},
        query_params={"key": "{{test_cred.api_key}}"},
        body_fields={"token": "{{test_cred.api_key}}"},
    )
    memory_store.register_usage(spec)

    result = memory_store.resolve_for_usage("test_cred")
    assert result["headers"]["Authorization"] == "Bearer test-key-123"
    assert result["params"]["key"] == "test-key-123"
    assert result["data"]["token"] == "test-key-123"
