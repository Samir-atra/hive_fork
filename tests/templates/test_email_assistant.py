import pytest
import asyncio
from examples.templates.email_assistant.agent import EmailAssistantAgent

@pytest.fixture
def agent():
    return EmailAssistantAgent()

def test_agent_graph_structure(agent):
    """Test that the agent graph structure is valid."""
    validation_result = agent.validate()
    assert validation_result["valid"] is True, f"Graph validation failed: {validation_result.get('errors')}"

def test_agent_info(agent):
    """Test that the agent info contains expected nodes."""
    info = agent.info()
    expected_nodes = ["fetch-emails", "classify-intent", "generate-reply", "execute-workflow", "report"]
    for node in expected_nodes:
        assert node in info["nodes"], f"Node {node} missing from agent info."
