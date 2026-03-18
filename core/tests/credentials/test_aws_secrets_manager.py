"""Tests for AWS Secrets Manager storage adapter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from framework.credentials.aws.secrets_manager import AWSSecretsManagerStorage
from framework.credentials.models import CredentialKey, CredentialObject, CredentialType


class TestAWSSecretsManagerStorage:
    @pytest.fixture
    def mock_boto3(self):
        """Mock boto3 for testing without AWS credentials."""
        with patch.dict(
            "sys.modules",
            {"boto3": MagicMock(), "botocore": MagicMock(), "botocore.exceptions": MagicMock()},
        ):
            import boto3

            session = MagicMock()
            client = MagicMock()
            session.client.return_value = client
            boto3.Session.return_value = session
            yield client

    def test_init_requires_boto3(self):
        with patch.dict("sys.modules", {"boto3": None}):
            with pytest.raises(ImportError, match="boto3"):
                AWSSecretsManagerStorage()

    def test_secret_name_construction(self, mock_boto3):
        storage = AWSSecretsManagerStorage(secret_prefix="myapp/creds")
        assert storage._secret_name("api_key") == "myapp/creds/api_key"

    def test_secret_name_sanitizes_paths(self, mock_boto3):
        storage = AWSSecretsManagerStorage()
        assert "_" in storage._secret_name("path\\with\\slashes")

    def test_save_creates_new_secret_when_not_exists(self, mock_boto3):
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}

        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                super().__init__(
                    f"An error occurred ({response['Error']['Code']}) "
                    f"when calling the {operation} operation"
                )

        mock_boto3.put_secret_value.side_effect = MockClientError(error_response, "PutSecretValue")

        storage = AWSSecretsManagerStorage()
        cred = CredentialObject(
            id="test_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret"))},
        )

        storage.save(cred)
        mock_boto3.create_secret.assert_called_once()

    def test_save_updates_existing_secret(self, mock_boto3):
        storage = AWSSecretsManagerStorage()
        cred = CredentialObject(
            id="test_api",
            credential_type=CredentialType.API_KEY,
            keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret"))},
        )

        storage.save(cred)
        mock_boto3.put_secret_value.assert_called_once()

    def test_load_returns_credential(self, mock_boto3):
        mock_boto3.get_secret_value.return_value = {
            "SecretString": json.dumps(
                {
                    "_type": "api_key",
                    "keys": {"api_key": {"name": "api_key", "value": "my-secret"}},
                    "id": "test_api",
                }
            )
        }

        storage = AWSSecretsManagerStorage()
        cred = storage.load("test_api")

        assert cred is not None
        assert cred.id == "test_api"
        assert cred.keys["api_key"].get_secret_value() == "my-secret"

    def test_load_returns_none_for_missing(self, mock_boto3):
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}

        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                super().__init__(
                    f"An error occurred ({response['Error']['Code']}) "
                    f"when calling the {operation} operation"
                )

        mock_boto3.get_secret_value.side_effect = MockClientError(error_response, "GetSecretValue")

        storage = AWSSecretsManagerStorage()
        assert storage.load("nonexistent") is None

    def test_delete_returns_true_on_success(self, mock_boto3):
        storage = AWSSecretsManagerStorage()
        assert storage.delete("test_api") is True
        mock_boto3.delete_secret.assert_called_once()

    def test_delete_returns_false_for_missing(self, mock_boto3):
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}

        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                super().__init__(
                    f"An error occurred ({response['Error']['Code']}) "
                    f"when calling the {operation} operation"
                )

        mock_boto3.delete_secret.side_effect = MockClientError(error_response, "DeleteSecret")

        storage = AWSSecretsManagerStorage()
        assert storage.delete("nonexistent") is False

    def test_list_all_with_pagination(self, mock_boto3):
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"SecretList": [{"Name": "hive/credentials/api1"}]},
            {"SecretList": [{"Name": "hive/credentials/api2"}]},
        ]
        mock_boto3.get_paginator.return_value = paginator

        storage = AWSSecretsManagerStorage()
        creds = storage.list_all()

        assert creds == ["api1", "api2"]

    def test_exists_returns_true(self, mock_boto3):
        storage = AWSSecretsManagerStorage()
        assert storage.exists("test_api") is True
        mock_boto3.describe_secret.assert_called_once()

    def test_exists_returns_false_for_missing(self, mock_boto3):
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}

        class MockClientError(Exception):
            def __init__(self, response, operation):
                self.response = response
                super().__init__(
                    f"An error occurred ({response['Error']['Code']}) "
                    f"when calling the {operation} operation"
                )

        mock_boto3.describe_secret.side_effect = MockClientError(error_response, "DescribeSecret")

        storage = AWSSecretsManagerStorage()
        assert storage.exists("nonexistent") is False

    def test_health_check_success(self, mock_boto3):
        with patch.object(storage := AWSSecretsManagerStorage(), "_session") as mock_session:
            sts_client = MagicMock()
            mock_session.client.return_value = sts_client
            assert storage.health_check() is True

    def test_health_check_failure(self, mock_boto3):
        with patch.object(storage := AWSSecretsManagerStorage(), "_session") as mock_session:
            sts_client = MagicMock()
            sts_client.get_caller_identity.side_effect = Exception("failed")
            mock_session.client.return_value = sts_client
            assert storage.health_check() is False


class TestOAuth2CredentialRoundTrip:
    @pytest.fixture
    def mock_boto3(self):
        with patch.dict(
            "sys.modules",
            {"boto3": MagicMock(), "botocore": MagicMock(), "botocore.exceptions": MagicMock()},
        ):
            import boto3

            session = MagicMock()
            client = MagicMock()
            session.client.return_value = client
            boto3.Session.return_value = session
            yield client

    def test_oauth2_credential_serialization(self, mock_boto3):
        storage = AWSSecretsManagerStorage()

        cred = CredentialObject(
            id="github_oauth",
            credential_type=CredentialType.OAUTH2,
            keys={
                "access_token": CredentialKey(name="access_token", value=SecretStr("gho_xxx")),
                "refresh_token": CredentialKey(name="refresh_token", value=SecretStr("ghr_yyy")),
            },
        )

        saved_data = None

        def capture_save(**kwargs):
            nonlocal saved_data
            saved_data = json.loads(kwargs["SecretString"])

        mock_boto3.put_secret_value.side_effect = capture_save

        storage.save(cred)

        assert saved_data["_type"] == "oauth2"
        assert saved_data["keys"]["access_token"]["value"] == "gho_xxx"
        assert saved_data["keys"]["refresh_token"]["value"] == "ghr_yyy"
