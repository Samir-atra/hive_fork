import pytest

from framework.credentials.models import (
    CredentialKeyNotFoundError,
    CredentialNotFoundError,
    CredentialObject,
)
from framework.credentials.template import TemplateResolver


def test_template_resolver_resolve(memory_store, sample_credential):
    # Setup
    memory_store.save_credential(sample_credential)
    resolver = TemplateResolver(memory_store)

    # Resolve specific key
    template = "Bearer {{test_cred.api_key}}"
    result = resolver.resolve(template)
    assert result == "Bearer test-key-123"

    # Resolve default key
    template_default = "Token {{test_cred}}"
    result_default = resolver.resolve(template_default)
    assert result_default == "Token test-key-123"


def test_template_resolver_resolve_headers_and_params(memory_store, sample_credential):
    memory_store.save_credential(sample_credential)
    resolver = TemplateResolver(memory_store)

    headers = {"Authorization": "Bearer {{test_cred.api_key}}", "X-Custom": "Value"}
    resolved_headers = resolver.resolve_headers(headers)
    assert resolved_headers["Authorization"] == "Bearer test-key-123"
    assert resolved_headers["X-Custom"] == "Value"

    params = {"key": "{{test_cred.api_key}}", "q": "search"}
    resolved_params = resolver.resolve_params(params)
    assert resolved_params["key"] == "test-key-123"
    assert resolved_params["q"] == "search"


def test_template_resolver_missing_credential(memory_store):
    resolver = TemplateResolver(memory_store)

    # Missing cred - fail_on_missing=True
    with pytest.raises(CredentialNotFoundError):
        resolver.resolve("Bearer {{missing_cred.api_key}}")

    # Missing cred - fail_on_missing=False
    result = resolver.resolve("Bearer {{missing_cred.api_key}}", fail_on_missing=False)
    assert result == "Bearer {{missing_cred.api_key}}"


def test_template_resolver_missing_key(memory_store, sample_credential):
    memory_store.save_credential(sample_credential)
    resolver = TemplateResolver(memory_store)

    # Missing key
    with pytest.raises(CredentialKeyNotFoundError):
        resolver.resolve("Bearer {{test_cred.missing_key}}")

    # No keys for default
    empty_cred = CredentialObject(id="empty_cred")
    memory_store.save_credential(empty_cred)
    with pytest.raises(CredentialKeyNotFoundError):
        resolver.resolve("Bearer {{empty_cred}}")


def test_template_resolver_extraction_and_validation(memory_store, sample_credential):
    memory_store.save_credential(sample_credential)
    resolver = TemplateResolver(memory_store)

    template = "Token {{test_cred.api_key}} and {{other_cred}} and {{test_cred.missing}}"

    # has_templates
    assert resolver.has_templates(template) is True
    assert resolver.has_templates("No templates here") is False

    # extract_references
    refs = resolver.extract_references(template)
    assert refs == [("test_cred", "api_key"), ("other_cred", None), ("test_cred", "missing")]

    # get_required_credentials
    required = resolver.get_required_credentials(template)
    assert required == ["test_cred", "other_cred"]

    # validate_references
    errors = resolver.validate_references(template)
    assert len(errors) == 2
    assert "Credential 'other_cred' not found" in errors
    assert "Key 'missing' not found in credential 'test_cred'" in errors
