"""Model versioning and rollback logic."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

HIVE_HOME = Path(os.environ.get("HIVE_HOME", Path.home() / ".hive"))
DEFAULT_REGISTRY_PATH = HIVE_HOME / "model_versions.json"


@dataclass
class ModelVersion:
    """A specific version of an AI model."""

    version: str
    provider_model_id: str
    metrics: dict[str, Any] = field(default_factory=dict)
    failures: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ModelVersionManager:
    """Manages AI model versions, dynamic switching, and rollback on failure."""

    _instance: "ModelVersionManager | None" = None

    def __init__(self, registry_path: Path | str | None = None):
        """Initialize ModelVersionManager.

        Args:
            registry_path: Path to the JSON registry file. Defaults to ~/.hive/model_versions.json.
        """
        self.registry_path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        self.registry: dict[str, dict[str, Any]] = self._load()

    @classmethod
    def default(cls) -> "ModelVersionManager":
        """Get the singleton default ModelVersionManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load registry from disk."""
        if not self.registry_path.exists():
            return {}
        try:
            with open(self.registry_path, encoding="utf-8-sig") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load model versions registry %s: %s",
                self.registry_path,
                e,
            )
            return {}

    def _save(self) -> None:
        """Save registry to disk."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, indent=2)
        except OSError as e:
            logger.error(
                "Failed to save model versions registry %s: %s",
                self.registry_path,
                e,
            )

    def register_version(
        self,
        model_id: str,
        version: str,
        provider_model_id: str,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Register a new model version.

        Args:
            model_id: The conceptual model ID (e.g., 'my-agent-model').
            version: The version string (e.g., 'v1', 'v2').
            provider_model_id: The actual provider model ID (e.g., 'gpt-4o').
            metrics: Optional dict of metrics for this version.
        """
        if model_id not in self.registry:
            self.registry[model_id] = {"active_version": version, "versions": {}}

        mv = ModelVersion(
            version=version,
            provider_model_id=provider_model_id,
            metrics=metrics or {},
        )

        # Convert dataclass to dict
        mv_dict = {
            "version": mv.version,
            "provider_model_id": mv.provider_model_id,
            "metrics": mv.metrics,
            "failures": mv.failures,
            "timestamp": mv.timestamp,
        }

        self.registry[model_id]["versions"][version] = mv_dict

        # Auto switch if it's the first version
        is_first = (
            "active_version" not in self.registry[model_id]
            or not self.registry[model_id]["active_version"]
        )
        if is_first:
            self.registry[model_id]["active_version"] = version

        self._save()
        logger.info(
            "Registered model %s version %s (maps to %s)",
            model_id,
            version,
            provider_model_id,
        )

    def switch_version(self, model_id: str, version: str) -> None:
        """Switch the active version of a model.

        Args:
            model_id: The conceptual model ID.
            version: The version to switch to.
        Raises:
            ValueError: If the model_id or version does not exist.
        """
        if model_id not in self.registry:
            raise ValueError(f"Model ID '{model_id}' not found in registry.")
        if version not in self.registry[model_id]["versions"]:
            raise ValueError(f"Version '{version}' not found for model '{model_id}'.")

        self.registry[model_id]["active_version"] = version
        self._save()
        logger.info("Switched model %s to version %s", model_id, version)

    def get_current_model(self, model_id: str) -> str:
        """Resolve a conceptual model ID to the active provider model ID.

        Args:
            model_id: The model string to resolve.

        Returns:
            The active provider model ID if found, otherwise returns the original `model_id`.
        """
        self.registry = self._load() # Reload to pick up CLI changes
        if model_id in self.registry:
            active_version = self.registry[model_id].get("active_version")
            if active_version and active_version in self.registry[model_id]["versions"]:
                return self.registry[model_id]["versions"][active_version]["provider_model_id"]
        return model_id
    def report_failure(self, model_id: str, failure_threshold: int | None = None) -> None:
        """Report a failure for the active version and rollback if it exceeds the threshold.

        Args:
            model_id: The conceptual model ID.
            failure_threshold: Number of failures before triggering a rollback.
        """
        if model_id not in self.registry:
            return

        active_version = self.registry[model_id].get("active_version")
        if not active_version or active_version not in self.registry[model_id]["versions"]:
            return

        version_data = self.registry[model_id]["versions"][active_version]
        version_data["failures"] = version_data.get("failures", 0) + 1

        logger.warning(
            "Reported failure for model %s version %s. Total failures: %d",
            model_id,
            active_version,
            version_data["failures"],
        )

        if failure_threshold is not None and version_data["failures"] >= failure_threshold:
            self.rollback(model_id)
        else:
            self._save()

    def rollback(self, model_id: str) -> bool:
        """Rollback to the immediately preceding registered version.

        Args:
            model_id: The conceptual model ID.

        Returns:
            True if rollback was successful, False otherwise.
        """
        if model_id not in self.registry:
            return False

        versions_dict = self.registry[model_id]["versions"]
        if len(versions_dict) <= 1:
            logger.warning("Cannot rollback model %s: no other versions available.", model_id)
            return False

        active_version = self.registry[model_id].get("active_version")

        # Sort versions by timestamp descending
        sorted_versions = sorted(
            versions_dict.items(),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True,
        )

        # Find the active version's index
        active_idx = -1
        for i, (ver, _) in enumerate(sorted_versions):
            if ver == active_version:
                active_idx = i
                break

        # The previous version is the one immediately AFTER the active version in descending order
        if active_idx != -1 and active_idx + 1 < len(sorted_versions):
            prev_ver = sorted_versions[active_idx + 1][0]
            self.switch_version(model_id, prev_ver)
            logger.info("Rolled back model %s from %s to %s", model_id, active_version, prev_ver)
            return True
        elif active_idx == -1 and sorted_versions:
            # If active version is somehow invalid, fallback to the newest
            newest_ver = sorted_versions[0][0]
            self.switch_version(model_id, newest_ver)
            logger.info("Rolled back model %s to newest %s", model_id, newest_ver)
            return True

        logger.warning("Cannot rollback model %s: active version is the oldest.", model_id)
        return False
    def get_version_info(self, model_id: str) -> dict[str, Any] | None:
        """Get information about a model and its versions."""
        return self.registry.get(model_id)

    def list_models(self) -> dict[str, dict[str, Any]]:
        """List all registered models and their versions."""
        return self.registry
