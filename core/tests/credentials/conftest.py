import pytest
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType
from framework.credentials.storage import InMemoryStorage
from framework.credentials.store import CredentialStore


@pytest.fixture
def memory_store():
    """CredentialStore with in-memory storage for testing."""
    return CredentialStore(storage=InMemoryStorage(), auto_refresh=False)


@pytest.fixture
def sample_credential():
    """Standard test credential."""
    return CredentialObject(
        id="test_cred",
        credential_type=CredentialType.API_KEY,
        keys={"api_key": CredentialKey(name="api_key", value=SecretStr("test-key-123"))},
    )


@pytest.fixture
def sample_oauth_credential():
    """Standard OAuth test credential."""
    return CredentialObject(
        id="test_oauth",
        credential_type=CredentialType.OAUTH2,
        keys={
            "access_token": CredentialKey(name="access_token", value=SecretStr("access-123")),
            "refresh_token": CredentialKey(name="refresh_token", value=SecretStr("refresh-123")),
        },
        provider_id="oauth2",
        auto_refresh=True,
    )
