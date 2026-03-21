import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure examples is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from examples.templates.inbound_lead_sentinel.agent import InboundLeadSentinel

from framework.graph.executor import ExecutionResult


# Monkeypatch mock execution since the real executor relies on the mock LLM which stalls
# because there are no actual events going back and forth.
class MockAgent(InboundLeadSentinel):
    async def run(self, context: dict, mock_mode=False, session_state=None) -> ExecutionResult:
        # Simulate run

        from examples.templates.inbound_lead_sentinel.nodes import (
            _enrich_leads,
            _intake_leads,
            _route_leads,
            _score_leads,
        )

        class MockContext:
            def __init__(self, data):
                self.memory = MagicMock()
                self._data = data.copy()

                def read(k, default=None):
                    return self._data.get(k, default)

                def write(k, v):
                    self._data[k] = v

                self.memory.read.side_effect = read
                self.memory.write.side_effect = write

        ctx = MockContext(context)
        await _intake_leads(ctx, None)
        await _enrich_leads(ctx, None)
        await _score_leads(ctx, None)
        await _route_leads(ctx, None)

        output = ctx._data
        return ExecutionResult(success=True, output=output)


@pytest.fixture
def agent():
    return MockAgent()


@pytest.mark.asyncio
async def test_agent_success_flow(agent):
    context_data = {
        "new_leads": [
            {"email": "ceo@enterprise.com", "name": "Jane Doe"},
            {"email": "founder@techstartup.io", "name": "John Smith"},
            {"email": "user@unknown.com", "name": "Unknown User"},
        ],
        "max_leads_per_batch": 50,
        "icp_score_threshold": 70,  # Adjusted to 70 for tests
    }

    result = await agent.run(context_data, mock_mode=True)

    assert result.success is True
    assert result.output.get("circuit_breaker_tripped") is False
    assert len(result.output.get("routed_leads", [])) == 1
    assert result.output.get("routed_leads")[0]["email"] == "ceo@enterprise.com"


@pytest.mark.asyncio
async def test_circuit_breaker(agent):
    context_data = {
        "new_leads": [{"email": f"user{i}@test.com"} for i in range(51)],
        "max_leads_per_batch": 50,
    }

    result = await agent.run(context_data, mock_mode=True)

    assert result.success is True
    assert result.output.get("circuit_breaker_tripped") is True
