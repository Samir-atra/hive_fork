"""Shared fixtures for credential store tests."""

import pytest
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType
from framework.credentials.storage import InMemoryStorage
from framework.credentials.store import CredentialStore


@pytest.fixture
def memory_store():
    """CredentialStore with in-memory storage for testing."""
    return CredentialStore(storage=InMemoryStorage())


@pytest.fixture
def sample_api_key_credential():
    """Standard API key test credential."""
    return CredentialObject(
        id="test_api",
        credential_type=CredentialType.API_KEY,
        keys={
            "api_key": CredentialKey(
                name="api_key",
                value=SecretStr("test-key-123"),
            )
        },
    )


@pytest.fixture
def sample_oauth2_credential():
    """OAuth2 test credential with access and refresh tokens."""
    return CredentialObject(
        id="oauth_test",
        credential_type=CredentialType.OAUTH2,
        keys={
            "access_token": CredentialKey(
                name="access_token",
                value=SecretStr("access-xxx"),
            ),
            "refresh_token": CredentialKey(
                name="refresh_token",
                value=SecretStr("refresh-yyy"),
            ),
        },
    )
