import pytest
from pydantic import SecretStr

from framework.credentials.models import (
    CredentialKey,
    CredentialObject,
    CredentialRefreshError,
)
from framework.credentials.storage import InMemoryStorage
from framework.credentials.store import CredentialStore


def test_refresh_credential_raises_error_when_no_provider():
    cred = CredentialObject(
        id="test_cred",
        keys={"access_token": CredentialKey(name="access_token", value=SecretStr("token"))},
        auto_refresh=True,
        provider_id="non_existent_provider",
    )

    store = CredentialStore(storage=InMemoryStorage({"test_cred": cred}))

    # Clear providers so it doesn't fall back to StaticProvider
    store._providers.clear()

    with pytest.raises(CredentialRefreshError) as exc_info:
        store._refresh_credential(cred)

    assert "No provider found for credential" in str(exc_info.value)
