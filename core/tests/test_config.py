"""Tests for framework/config.py - Hive configuration loading."""

import logging

from framework.config import get_api_base, get_hive_config, get_preferred_model


class TestGetHiveConfig:
    """Test get_hive_config() logs warnings on parse errors."""

    def test_logs_warning_on_malformed_json(self, tmp_path, monkeypatch, caplog):
        """Test that malformed JSON logs warning and returns empty dict."""
        config_file = tmp_path / "configuration.json"
        config_file.write_text('{"broken": }')

        monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)

        with caplog.at_level(logging.WARNING):
            result = get_hive_config()

        assert result == {}
        assert "Failed to load Hive config" in caplog.text
        assert str(config_file) in caplog.text


class TestOpenRouterConfig:
    """OpenRouter config composition and fallback behavior."""

    def test_get_preferred_model_for_openrouter(self, tmp_path, monkeypatch):
        config_file = tmp_path / "configuration.json"
        config_file.write_text(
            '{"llm":{"provider":"openrouter","model":"x-ai/grok-4.20-beta"}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)

        assert get_preferred_model() == "openrouter/x-ai/grok-4.20-beta"

    def test_get_preferred_model_normalizes_openrouter_prefixed_model(self, tmp_path, monkeypatch):
        config_file = tmp_path / "configuration.json"
        config_file.write_text(
            '{"llm":{"provider":"openrouter","model":"openrouter/x-ai/grok-4.20-beta"}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)

        assert get_preferred_model() == "openrouter/x-ai/grok-4.20-beta"

    def test_get_api_base_falls_back_to_openrouter_default(self, tmp_path, monkeypatch):
        config_file = tmp_path / "configuration.json"
        config_file.write_text(
            '{"llm":{"provider":"openrouter","model":"x-ai/grok-4.20-beta"}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)

        assert get_api_base() == "https://openrouter.ai/api/v1"

    def test_get_api_base_keeps_explicit_openrouter_api_base(self, tmp_path, monkeypatch):
        config_file = tmp_path / "configuration.json"
        config_file.write_text(
            '{"llm":{"provider":"openrouter","model":"x-ai/grok-4.20-beta","api_base":"https://proxy.example/v1"}}',
            encoding="utf-8",
        )
        monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)

        assert get_api_base() == "https://proxy.example/v1"


def test_get_hive_config_hive_env(monkeypatch, tmp_path):
    import json

    monkeypatch.setenv("HIVE_ENV", "dev")
    config_file = tmp_path / "configuration.json"
    env_config_file = tmp_path / "configuration.dev.json"

    # Create the env specific config file
    with open(env_config_file, "w") as f:
        json.dump({"env": "dev"}, f)

    monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)
    from framework.config import get_hive_config

    config = get_hive_config()
    assert config == {"env": "dev"}


def test_get_hive_config_fallback(monkeypatch, tmp_path):
    import json

    monkeypatch.setenv("HIVE_ENV", "prod")
    config_file = tmp_path / "configuration.json"

    # Create only the fallback config file
    with open(config_file, "w") as f:
        json.dump({"env": "fallback"}, f)

    monkeypatch.setattr("framework.config.HIVE_CONFIG_FILE", config_file)
    from framework.config import get_hive_config

    config = get_hive_config()
    assert config == {"env": "fallback"}
