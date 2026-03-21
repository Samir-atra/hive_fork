from datetime import UTC, datetime, timedelta

from pydantic import SecretStr

from framework.credentials.models import (
    CredentialKey,
    CredentialObject,
    CredentialUsageSpec,
)


def test_credential_key_is_expired():
    """Test the expiration logic of CredentialKey."""
    # No expiration
    key = CredentialKey(name="test", value=SecretStr("value"))
    assert not key.is_expired

    # Future expiration
    future = datetime.now(UTC) + timedelta(days=1)
    key_future = CredentialKey(name="test", value=SecretStr("value"), expires_at=future)
    assert not key_future.is_expired

    # Past expiration
    past = datetime.now(UTC) - timedelta(days=1)
    key_past = CredentialKey(name="test", value=SecretStr("value"), expires_at=past)
    assert key_past.is_expired


def test_credential_key_secret_masking(caplog):
    """Test that SecretStr prevents accidental logging of the secret value."""
    key = CredentialKey(name="api_key", value=SecretStr("super_secret_value"))

    # Just printing or converting to dict/json shouldn't expose the value
    model_dump = key.model_dump()
    assert isinstance(model_dump["value"], SecretStr)

    model_json = key.model_dump_json()
    assert "super_secret_value" not in model_json
    assert "**********" in model_json

    # Explicitly asking for secret value works
    assert key.get_secret_value() == "super_secret_value"


def test_credential_object_get_default_key():
    """Test default key retrieval order."""
    # Empty keys
    obj_empty = CredentialObject(id="empty")
    assert obj_empty.get_default_key() is None

    # value priority
    obj_value = CredentialObject(
        id="test",
        keys={
            "api_key": CredentialKey(name="api_key", value=SecretStr("api")),
            "value": CredentialKey(name="value", value=SecretStr("val")),
        },
    )
    assert obj_value.get_default_key() == "val"

    # api_key priority
    obj_api = CredentialObject(
        id="test",
        keys={
            "access_token": CredentialKey(name="access_token", value=SecretStr("access")),
            "api_key": CredentialKey(name="api_key", value=SecretStr("api")),
        },
    )
    assert obj_api.get_default_key() == "api"

    # access_token priority
    obj_access = CredentialObject(
        id="test",
        keys={
            "other": CredentialKey(name="other", value=SecretStr("oth")),
            "access_token": CredentialKey(name="access_token", value=SecretStr("access")),
        },
    )
    assert obj_access.get_default_key() == "access"

    # first key fallback
    obj_first = CredentialObject(
        id="test",
        keys={
            "first_key": CredentialKey(name="first_key", value=SecretStr("first")),
            "second_key": CredentialKey(name="second_key", value=SecretStr("second")),
        },
    )
    assert obj_first.get_default_key() == "first"


def test_credential_object_needs_refresh_and_is_valid():
    """Test the validity and refresh status of CredentialObject."""
    past = datetime.now(UTC) - timedelta(days=1)
    future = datetime.now(UTC) + timedelta(days=1)

    obj = CredentialObject(
        id="test",
        keys={
            "expired": CredentialKey(name="expired", value=SecretStr("val1"), expires_at=past),
            "valid": CredentialKey(name="valid", value=SecretStr("val2"), expires_at=future),
        },
    )
    # One key is expired, so it needs refresh
    assert obj.needs_refresh is True
    # At least one key is valid, so it is valid
    assert obj.is_valid is True

    obj_all_expired = CredentialObject(
        id="test",
        keys={
            "expired": CredentialKey(name="expired", value=SecretStr("val1"), expires_at=past),
        },
    )
    assert obj_all_expired.is_valid is False
    assert obj_all_expired.needs_refresh is True

    obj_no_keys = CredentialObject(id="test")
    assert obj_no_keys.is_valid is False
    assert obj_no_keys.needs_refresh is False


def test_credential_object_identity_and_alias():
    """Test identity and alias extraction from keys."""
    obj = CredentialObject(
        id="test",
        keys={
            "_identity_email": CredentialKey(
                name="_identity_email", value=SecretStr("test@example.com")
            ),
            "_identity_workspace": CredentialKey(
                name="_identity_workspace", value=SecretStr("work1")
            ),
            "_alias": CredentialKey(name="_alias", value=SecretStr("my_alias")),
            "_integration_type": CredentialKey(name="_integration_type", value=SecretStr("google")),
        },
    )

    identity = obj.identity
    assert identity.email == "test@example.com"
    assert identity.workspace == "work1"
    assert identity.username is None
    assert identity.label == "test@example.com"
    assert identity.is_known is True

    assert obj.alias == "my_alias"
    assert obj.provider_type == "google"

    # Test set_identity
    obj2 = CredentialObject(id="test2")
    obj2.set_identity(username="user1", email="user1@example.com")
    assert obj2.keys["_identity_username"].get_secret_value() == "user1"
    assert obj2.keys["_identity_email"].get_secret_value() == "user1@example.com"
    assert obj2.identity.username == "user1"


def test_credential_object_record_usage():
    """Test usage recording."""
    obj = CredentialObject(id="test")
    assert obj.use_count == 0
    assert obj.last_used is None

    obj.record_usage()
    assert obj.use_count == 1
    assert obj.last_used is not None


def test_credential_usage_spec_initialization():
    """Test CredentialUsageSpec handles initial values properly."""
    spec = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"Authorization": "Bearer {{test_cred.api_key}}"},
    )
    assert spec.credential_id == "test_cred"
    assert "api_key" in spec.required_keys
    assert spec.headers["Authorization"] == "Bearer {{test_cred.api_key}}"
