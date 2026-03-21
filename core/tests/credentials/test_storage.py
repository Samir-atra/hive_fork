import json

import pytest

from framework.credentials.models import CredentialObject, CredentialType
from framework.credentials.storage import (
    CompositeStorage,
    EncryptedFileStorage,
    EnvVarStorage,
    InMemoryStorage,
)


def test_in_memory_storage(sample_credential):
    storage = InMemoryStorage()

    # Save
    storage.save(sample_credential)
    assert storage.exists("test_cred")

    # Load
    loaded = storage.load("test_cred")
    assert loaded is not None
    assert loaded.id == "test_cred"
    assert loaded.get_key("api_key") == "test-key-123"

    # List
    assert "test_cred" in storage.list_all()

    # Delete
    assert storage.delete("test_cred") is True
    assert storage.exists("test_cred") is False
    assert storage.delete("test_cred") is False


def test_env_var_storage_load_success(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "env-secret-123")
    storage = EnvVarStorage(env_mapping={"test_cred": "TEST_API_KEY"})

    # Check exists
    assert storage.exists("test_cred")

    # Check load
    loaded = storage.load("test_cred")
    assert loaded is not None
    assert loaded.get_key("api_key") == "env-secret-123"
    assert loaded.credential_type == CredentialType.API_KEY


def test_env_var_storage_missing_var():
    storage = EnvVarStorage(env_mapping={"test_cred": "NON_EXISTENT_VAR"})
    assert not storage.exists("test_cred")
    assert storage.load("test_cred") is None


def test_env_var_storage_read_only(sample_credential):
    storage = EnvVarStorage()

    with pytest.raises(NotImplementedError):
        storage.save(sample_credential)

    with pytest.raises(NotImplementedError):
        storage.delete("test_cred")


def test_encrypted_file_storage(tmp_path, sample_credential):
    # Setup test directory
    storage_dir = tmp_path / ".hive" / "credentials"

    storage = EncryptedFileStorage(base_path=storage_dir)

    # Save credential
    storage.save(sample_credential)
    assert storage.exists("test_cred")

    # Check physical file exists
    assert (storage_dir / "credentials" / "test_cred.enc").exists()

    # Check index
    index_path = storage_dir / "metadata" / "index.json"
    assert index_path.exists()
    with open(index_path) as f:
        index_data = json.load(f)
    assert "test_cred" in index_data["credentials"]

    # Load credential
    loaded = storage.load("test_cred")
    assert loaded is not None
    assert loaded.id == "test_cred"
    assert loaded.get_key("api_key") == "test-key-123"

    # List
    assert "test_cred" in storage.list_all()

    # Delete
    assert storage.delete("test_cred") is True
    assert not storage.exists("test_cred")
    assert not (storage_dir / "credentials" / "test_cred.enc").exists()

    # Check index updated
    with open(index_path) as f:
        index_data = json.load(f)
    assert "test_cred" not in index_data["credentials"]


def test_encrypted_file_storage_path_sanitization(tmp_path, sample_credential):
    storage_dir = tmp_path / "creds"
    storage = EncryptedFileStorage(base_path=storage_dir)

    # Alter id to have path traversal chars
    sample_credential.id = "../../../etc/passwd"
    storage.save(sample_credential)

    # The saved file should have underscores instead of slashes/dots
    safe_id = sample_credential.id.replace("/", "_").replace("\\", "_").replace("..", "_")
    assert safe_id == "___.._.._etc_passwd" or safe_id == "______etc_passwd"
    assert (storage_dir / "credentials" / f"{safe_id}.enc").exists()


def test_composite_storage(sample_credential):
    primary = InMemoryStorage()
    fallback = InMemoryStorage()

    # Put different credentials in each
    fallback.save(sample_credential)

    second_cred = CredentialObject(id="second_cred")
    primary.save(second_cred)

    storage = CompositeStorage(primary=primary, fallbacks=[fallback])

    # exists checks both
    assert storage.exists("test_cred")
    assert storage.exists("second_cred")
    assert not storage.exists("missing")

    # load checks both
    loaded_from_fallback = storage.load("test_cred")
    assert loaded_from_fallback is not None
    assert loaded_from_fallback.id == "test_cred"

    loaded_from_primary = storage.load("second_cred")
    assert loaded_from_primary is not None
    assert loaded_from_primary.id == "second_cred"

    # delete only acts on primary
    assert storage.delete("test_cred") is False  # In fallback, not deleted
    assert storage.delete("second_cred") is True  # In primary, deleted

    # list combines both
    all_creds = storage.list_all()
    assert "test_cred" in all_creds
    assert "second_cred" not in all_creds  # deleted
