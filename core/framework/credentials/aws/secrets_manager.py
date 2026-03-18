"""AWS Secrets Manager storage backend."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import SecretStr

from framework.credentials.models import (
    CredentialDecryptionError,
    CredentialObject,
)
from framework.credentials.storage import CredentialStorage

logger = logging.getLogger(__name__)

class AWSSecretsManagerStorage(CredentialStorage):
    """
    AWS Secrets Manager storage backend.

    Stores credentials as JSON in AWS Secrets Manager.
    Uses boto3 to communicate with AWS.

    Example:
        storage = AWSSecretsManagerStorage(
            secret_prefix="hive/credentials",
            region_name="us-east-1"
        )
    """

    def __init__(
        self,
        secret_prefix: str = "hive/credentials",
        region_name: str | None = None,
        profile_name: str | None = None,
        endpoint_url: str | None = None,
    ):
        """
        Initialize AWS Secrets Manager storage.

        Args:
            secret_prefix: Prefix for secret names (e.g., 'hive/credentials')
            region_name: AWS region name
            profile_name: AWS profile name for auth
            endpoint_url: Custom endpoint URL (e.g. for LocalStack)
        """
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "AWS Secrets Manager support requires 'boto3'. "
                "Install with: uv pip install boto3"
            ) from e

        self.secret_prefix = secret_prefix.strip("/")

        # Initialize boto3 session and client
        session_kwargs = {}
        if region_name:
            session_kwargs["region_name"] = region_name
        if profile_name:
            session_kwargs["profile_name"] = profile_name

        self._session = boto3.Session(**session_kwargs)

        client_kwargs = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        self._client = self._session.client("secretsmanager", **client_kwargs)

    def _secret_name(self, credential_id: str) -> str:
        """Construct the full secret name from ID."""
        # Sanitize credential_id
        safe_id = credential_id.replace("\\", "_").replace("..", "_")
        if self.secret_prefix:
            return f"{self.secret_prefix}/{safe_id}"
        return safe_id

    def _serialize_credential(self, credential: CredentialObject) -> str:
        """Convert credential to a JSON string for storage."""
        data = credential.model_dump(mode="json")

        # Extract actual secret values
        for key_name, key_data in data.get("keys", {}).items():
            if "value" in key_data:
                actual_key = credential.keys.get(key_name)
                if actual_key:
                    key_data["value"] = actual_key.get_secret_value()

        # Store credential_type in a special field for backward compatibility
        data["_type"] = credential.credential_type.value

        return json.dumps(data)

    def _deserialize_credential(self, data: dict[str, Any]) -> CredentialObject:
        """Reconstruct credential from dictionary."""
        # Handle older formats that might just be flat keys
        if "keys" not in data and "id" not in data:
            # It's likely a raw secret without our metadata structure
            raise ValueError("Secret does not match expected CredentialObject schema")

        # Convert plain values back to SecretStr
        for key_data in data.get("keys", {}).values():
            if "value" in key_data and isinstance(key_data["value"], str):
                key_data["value"] = SecretStr(key_data["value"])

        # Remove the internal _type field if it exists
        data.pop("_type", None)

        return CredentialObject.model_validate(data)

    def save(self, credential: CredentialObject) -> None:
        """Save a credential to AWS Secrets Manager."""
        secret_name = self._secret_name(credential.id)
        secret_string = self._serialize_credential(credential)

        try:
            # Try to update if it exists
            self._client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_string
            )
            logger.debug(f"Updated credential '{credential.id}' in AWS Secrets Manager")
        except Exception as e:
            is_not_found = False

            # Since botocore uses e.response, we check that
            if hasattr(e, "response") and isinstance(e.response, dict):
                err = e.response.get("Error", {})
                if err.get("Code") == "ResourceNotFoundException":
                    is_not_found = True

            if is_not_found:
                # Secret does not exist, create it
                # Secret does not exist, create it
                description = credential.description or f"Hive credential: {credential.id}"
                tags = [{"Key": "hive_credential_id", "Value": credential.id}]
                if credential.credential_type:
                    tags.append({
                        "Key": "hive_credential_type",
                        "Value": credential.credential_type.value
                    })

                self._client.create_secret(
                    Name=secret_name,
                    Description=description,
                    SecretString=secret_string,
                    Tags=tags
                )
                logger.debug(f"Created new credential '{credential.id}' in AWS Secrets Manager")
            else:
                raise

    def load(self, credential_id: str) -> CredentialObject | None:
        """Load a credential from AWS Secrets Manager."""
        secret_name = self._secret_name(credential_id)

        try:
            response = self._client.get_secret_value(SecretId=secret_name)
        except Exception as e:
            is_not_found = False

            # Since botocore uses e.response, we check that
            if hasattr(e, "response") and isinstance(e.response, dict):
                err = e.response.get("Error", {})
                if err.get("Code") == "ResourceNotFoundException":
                    is_not_found = True

            if is_not_found:
                return None
            raise

        if "SecretString" not in response:
            logger.error(f"Secret '{secret_name}' does not contain a string value")
            raise CredentialDecryptionError("Secret is binary, expected string JSON")

        try:
            data = json.loads(response["SecretString"])
            # Ensure the ID matches what was requested
            if "id" not in data:
                data["id"] = credential_id
            return self._deserialize_credential(data)
        except Exception as e:
            raise CredentialDecryptionError(
                f"Failed to parse credential '{credential_id}': {e}"
            ) from e

    def delete(self, credential_id: str) -> bool:
        """Delete a credential from AWS Secrets Manager."""
        secret_name = self._secret_name(credential_id)

        try:
            # ForceDeleteWithoutRecovery=True ensures immediate deletion without
            # the standard 7-30 day recovery window, making tests and typical
            # development flows easier. In production you might want recovery.
            self._client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True
            )
            logger.debug(f"Deleted credential '{credential_id}' from AWS Secrets Manager")
            return True
        except Exception as e:
            is_not_found = False

            # Since botocore uses e.response, we check that
            if hasattr(e, "response") and isinstance(e.response, dict):
                err = e.response.get("Error", {})
                if err.get("Code") == "ResourceNotFoundException":
                    is_not_found = True

            if is_not_found:
                return False
            raise

    def list_all(self) -> list[str]:
        """List all credential IDs in AWS Secrets Manager."""
        paginator = self._client.get_paginator("list_secrets")
        credential_ids = []

        # Filter secrets by prefix if set
        filters = []
        if self.secret_prefix:
            filters.append({
                "Key": "name",
                "Values": [f"{self.secret_prefix}/"]
            })

        kwargs = {}
        if filters:
            kwargs["Filters"] = filters

        for page in paginator.paginate(**kwargs):
            for secret in page.get("SecretList", []):
                name = secret["Name"]
                # Extract the ID from the full name
                if self.secret_prefix and name.startswith(f"{self.secret_prefix}/"):
                    credential_ids.append(name[len(f"{self.secret_prefix}/"):])
                else:
                    credential_ids.append(name)

        return credential_ids

    def exists(self, credential_id: str) -> bool:
        """Check if a credential exists in AWS Secrets Manager."""
        secret_name = self._secret_name(credential_id)

        try:
            self._client.describe_secret(SecretId=secret_name)
            return True
        except Exception as e:
            is_not_found = False

            # Since botocore uses e.response, we check that
            if hasattr(e, "response") and isinstance(e.response, dict):
                err = e.response.get("Error", {})
                if err.get("Code") == "ResourceNotFoundException":
                    is_not_found = True

            if is_not_found:
                return False
            raise

    def health_check(self) -> bool:
        """Check if AWS credentials are valid and STS is reachable."""
        try:
            sts_client = self._session.client("sts")
            sts_client.get_caller_identity()
            return True
        except Exception:
            return False
