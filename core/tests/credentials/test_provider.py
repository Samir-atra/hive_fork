from datetime import UTC, datetime, timedelta

import pytest

from framework.credentials.models import (
    CredentialObject,
    CredentialRefreshError,
    CredentialType,
)
from framework.credentials.provider import BearerTokenProvider, StaticProvider


def test_static_provider_refresh_and_validate(sample_credential):
    provider = StaticProvider()

    assert provider.provider_id == "static"
    assert CredentialType.API_KEY in provider.supported_types
    assert provider.can_handle(sample_credential) is True

    # Static credential should not need refresh
    assert provider.should_refresh(sample_credential) is False

    # Refresh should return the same credential
    refreshed = provider.refresh(sample_credential)
    assert refreshed is sample_credential

    # Valid if it has keys with non-empty values
    assert provider.validate(sample_credential) is True

    # Invalid if no keys
    empty_cred = CredentialObject(id="empty", credential_type=CredentialType.API_KEY)
    assert provider.validate(empty_cred) is False


def test_bearer_token_provider(sample_credential):
    provider = BearerTokenProvider()

    assert provider.provider_id == "bearer_token"
    assert CredentialType.BEARER_TOKEN in provider.supported_types

    # Change type for testing
    sample_credential.credential_type = CredentialType.BEARER_TOKEN

    # Add an access token key
    future = datetime.now(UTC) + timedelta(days=1)
    sample_credential.set_key("access_token", "token-123", expires_at=future)

    # Validate it should be valid since token is in the future
    assert provider.validate(sample_credential) is True

    # Should not refresh because expiration is far
    assert provider.should_refresh(sample_credential) is False

    # Nearing expiration should trigger refresh
    near_future = datetime.now(UTC) + timedelta(minutes=4)
    sample_credential.set_key("access_token", "token-123", expires_at=near_future)
    assert provider.should_refresh(sample_credential) is True

    # Bearer tokens cannot be refreshed
    with pytest.raises(CredentialRefreshError):
        provider.refresh(sample_credential)
