from framework.config import RuntimeConfig
import os

def get_config() -> RuntimeConfig:
    """Get the runtime configuration with observability explicitly enabled."""
    config = RuntimeConfig()
    # Force observability to True for demonstration if not set
    if not config.observability.get("enabled"):
        config.observability["enabled"] = True
        config.observability["metrics_file"] = os.path.expanduser("~/hive_observability_demo.jsonl")
    return config
