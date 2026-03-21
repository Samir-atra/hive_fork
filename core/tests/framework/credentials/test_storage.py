import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from framework.credentials.models import (
    CredentialDecryptionError,
    CredentialKey,
    CredentialObject,
    CredentialType,
)
from framework.credentials.storage import EncryptedFileStorage


@pytest.fixture
def mock_credential():
    return CredentialObject(
        id="test_cred",
        credential_type=CredentialType.API_KEY,
        keys={"api_key": CredentialKey(name="api_key", value=SecretStr("super_secret"))},
        description="A test credential",
    )


def test_encrypted_storage_auto_persists_key(tmp_path, monkeypatch):
    """Test that generated key is automatically persisted with secure permissions."""
    monkeypatch.delenv("HIVE_CREDENTIAL_KEY", raising=False)
    monkeypatch.setenv("HIVE_STRICT_CREDENTIAL_MODE", "false")

    storage = EncryptedFileStorage(base_path=tmp_path)

    key_file = tmp_path / ".encryption_key"
    assert key_file.exists()
    assert key_file.stat().st_mode & 0o777 == 0o600

    # Reload storage, should use the persisted key
    storage2 = EncryptedFileStorage(base_path=tmp_path)
    assert storage._key == storage2._key


def test_encrypted_storage_strict_mode_raises(tmp_path, monkeypatch):
    """Test that strict mode requires the environment variable."""
    monkeypatch.delenv("HIVE_CREDENTIAL_KEY", raising=False)
    monkeypatch.setenv("HIVE_STRICT_CREDENTIAL_MODE", "true")

    with pytest.raises(RuntimeError, match="Production mode requires"):
        EncryptedFileStorage(base_path=tmp_path)


def test_encrypted_storage_path_traversal(tmp_path, mock_credential):
    """Test path traversal characters are sanitized."""
    key = Fernet.generate_key()
    storage = EncryptedFileStorage(base_path=tmp_path, encryption_key=key)

    mock_credential.id = "../../../etc/passwd"
    storage.save(mock_credential)

    # Should be sanitized to ______etc_passwd (because each .. -> _, / -> _, / -> _)
    assert not (tmp_path / "../../../etc/passwd.enc").exists()
    assert (tmp_path / "credentials/______etc_passwd.enc").exists()


def test_encrypted_storage_error_sanitization(tmp_path, mock_credential):
    """Test that decryption errors do not leak implementation details."""
    key1 = Fernet.generate_key()
    storage1 = EncryptedFileStorage(base_path=tmp_path, encryption_key=key1)
    storage1.save(mock_credential)

    # Try reading with a different key
    key2 = Fernet.generate_key()
    storage2 = EncryptedFileStorage(base_path=tmp_path, encryption_key=key2)

    with pytest.raises(CredentialDecryptionError) as exc:
        storage2.load("test_cred")

    # Error message should be generic, not a cryptography exception
    assert "Verify HIVE_CREDENTIAL_KEY" in str(exc.value)
    # Check that it suppressed original exception
    assert exc.value.__cause__ is None


def test_encrypted_storage_rotate_key(tmp_path, mock_credential):
    """Test that keys can be rotated properly."""
    key1 = Fernet.generate_key()
    storage = EncryptedFileStorage(base_path=tmp_path, encryption_key=key1)

    storage.save(mock_credential)

    # Rotate
    key2 = Fernet.generate_key()
    log_path = tmp_path / "rotation_log.json"
    results = storage.rotate_key(key2, audit_log_path=log_path)

    assert results["success"] == 1
    assert "test_cred" in results["rotated"]

    assert log_path.exists()

    # Verify new key is set
    assert storage._key == key2

    # Verify we can read it with the new key storage instance
    storage2 = EncryptedFileStorage(base_path=tmp_path, encryption_key=key2)
    loaded = storage2.load("test_cred")
    assert loaded.keys["api_key"].get_secret_value() == "super_secret"
