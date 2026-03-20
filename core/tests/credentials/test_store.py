import pytest
from framework.credentials import CredentialStore, CredentialUsageSpec
from framework.credentials.models import CredentialNotFoundError

def test_resolve_for_usage_without_credential_id_in_template():
    store = CredentialStore.for_testing({"test_cred": {"api_key": "my-secret-key"}})

    usage = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"X-API-Key": "{{api_key}}"}  # Template without credential ID
    )
    store.register_usage(usage)

    result = store.resolve_for_usage("test_cred")

    assert "headers" in result
    assert result["headers"] == {"X-API-Key": "my-secret-key"}

def test_resolve_for_usage_with_credential_id_in_template():
    store = CredentialStore.for_testing({"test_cred": {"api_key": "my-secret-key"}})

    usage = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"X-API-Key": "{{test_cred.api_key}}"}  # Template with credential ID
    )
    store.register_usage(usage)

    result = store.resolve_for_usage("test_cred")

    assert "headers" in result
    assert result["headers"] == {"X-API-Key": "my-secret-key"}

def test_resolve_for_usage_default_key():
    store = CredentialStore.for_testing({"test_cred": {"api_key": "my-secret-key"}})

    usage = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"Authorization": "Bearer {{test_cred}}"}  # Default key
    )
    store.register_usage(usage)

    result = store.resolve_for_usage("test_cred")

    assert "headers" in result
    assert result["headers"] == {"Authorization": "Bearer my-secret-key"}

def test_resolve_for_usage_other_credential_id():
    store = CredentialStore.for_testing({
        "test_cred": {"api_key": "my-secret-key"},
        "other_cred": {"token": "other-token"}
    })

    usage = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        headers={"X-Other-Token": "{{other_cred.token}}"}  # Referencing another credential
    )
    store.register_usage(usage)

    result = store.resolve_for_usage("test_cred")

    assert "headers" in result
    assert result["headers"] == {"X-Other-Token": "other-token"}


def test_resolve_for_usage_non_template_body():
    store = CredentialStore.for_testing({"test_cred": {"api_key": "my-secret-key"}})

    usage = CredentialUsageSpec(
        credential_id="test_cred",
        required_keys=["api_key"],
        body_fields={
            "api_key": "{{api_key}}",
            "literal_str": "not-a-template"
        }
    )
    store.register_usage(usage)

    result = store.resolve_for_usage("test_cred")

    assert "data" in result
    assert result["data"]["api_key"] == "my-secret-key"
    assert result["data"]["literal_str"] == "not-a-template"
