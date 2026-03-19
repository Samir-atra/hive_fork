import json
import os

def test_analytics_agent_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'agent.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    assert config["name"] == "analytics_agent"
    assert "analyze_data" in config["tools"]
    assert "generate_visualization" in config["tools"]
