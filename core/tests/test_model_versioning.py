"""Tests for ModelVersionManager."""

from pathlib import Path

import pytest

from framework.llm.versioning import ModelVersionManager


@pytest.fixture
def temp_registry(tmp_path: Path) -> ModelVersionManager:
    """Provide a ModelVersionManager with a temporary registry file."""
    registry_file = tmp_path / "model_versions.json"
    manager = ModelVersionManager(registry_path=registry_file)
    # Clear in-memory state in case it leaked
    manager.registry = {}
    return manager


def test_register_and_switch_version(temp_registry: ModelVersionManager):
    """Test registering and switching model versions."""
    # First registration should become active
    temp_registry.register_version(
        model_id="agent-model",
        version="v1",
        provider_model_id="gpt-3.5",
    )

    assert temp_registry.get_current_model("agent-model") == "gpt-3.5"
    info = temp_registry.get_version_info("agent-model")
    assert info is not None
    assert info["active_version"] == "v1"

    # Second registration does not automatically switch
    temp_registry.register_version(
        model_id="agent-model",
        version="v2",
        provider_model_id="gpt-4o",
    )

    assert temp_registry.get_current_model("agent-model") == "gpt-3.5"

    # Switch manually
    temp_registry.switch_version("agent-model", "v2")
    assert temp_registry.get_current_model("agent-model") == "gpt-4o"
    info = temp_registry.get_version_info("agent-model")
    assert info is not None
    assert info["active_version"] == "v2"


def test_failure_and_rollback(temp_registry: ModelVersionManager):
    """Test that tracking failures triggers a rollback."""
    # Register v1 and v2
    temp_registry.register_version("model1", "v1", "gpt-3.5")
    temp_registry.register_version("model1", "v2", "gpt-4")

    # Switch to v2
    temp_registry.switch_version("model1", "v2")
    assert temp_registry.get_current_model("model1") == "gpt-4"

    # Report failures below threshold
    temp_registry.report_failure("model1", failure_threshold=2)
    assert temp_registry.get_current_model("model1") == "gpt-4"

    # Report failure that hits the threshold
    temp_registry.report_failure("model1", failure_threshold=2)
    # Should rollback to the other available version (v1)
    assert temp_registry.get_current_model("model1") == "gpt-3.5"


def test_unregistered_model_fallback(temp_registry: ModelVersionManager):
    """Test that get_current_model returns the original string if not registered."""
    assert temp_registry.get_current_model("unknown-model") == "unknown-model"


def test_persistence(tmp_path: Path):
    """Test that registry persists to disk correctly."""
    registry_file = tmp_path / "model_versions.json"

    # Create and save
    manager1 = ModelVersionManager(registry_path=registry_file)
    manager1.registry = {}
    manager1.register_version("test-model", "v1", "provider-v1")

    # Read back with a new instance
    manager2 = ModelVersionManager(registry_path=registry_file)
    assert manager2.get_current_model("test-model") == "provider-v1"
