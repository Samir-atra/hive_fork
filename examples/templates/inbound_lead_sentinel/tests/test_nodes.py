import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from examples.templates.inbound_lead_sentinel.nodes import (
    _enrich_leads,
    _intake_leads,
    _route_leads,
    _score_leads,
    intake_node,
)

from framework.graph.node import NodeContext, SharedMemory
from framework.runtime.core import Runtime


@pytest.fixture
def mock_context():
    memory = SharedMemory()
    runtime = MagicMock(spec=Runtime)
    return NodeContext(
        runtime=runtime,
        node_id="test-node",
        node_spec=intake_node,
        memory=memory,
    )


@pytest.mark.asyncio
async def test_intake_node(mock_context):
    mock_context.memory.write("new_leads", [{"email": "a@b.com"}])
    mock_context.memory.write("max_leads_per_batch", 50)

    result = await _intake_leads(mock_context, None)

    assert result.success is True
    assert mock_context.memory.read("circuit_breaker_tripped") is False
    assert mock_context.memory.read("processing_leads") == [{"email": "a@b.com"}]


@pytest.mark.asyncio
async def test_enrich_node(mock_context):
    mock_context.memory.write(
        "processing_leads", [{"email": "ceo@enterprise.com"}, {"email": "founder@techstartup.io"}]
    )

    result = await _enrich_leads(mock_context, None)

    assert result.success is True
    enriched = mock_context.memory.read("enriched_leads")
    assert len(enriched) == 2
    assert enriched[0]["company_size"] == 1000
    assert enriched[0]["revenue"] == "$10M+"
    assert enriched[1]["industry"] == "Tech"


@pytest.mark.asyncio
async def test_score_node(mock_context):
    mock_context.memory.write(
        "enriched_leads",
        [
            {"email": "ceo@ent.com", "company_size": 1000, "industry": "Other", "revenue": "$10M+"},
            {"email": "f@tech.io", "company_size": 50, "industry": "Tech", "revenue": "<$1M"},
        ],
    )

    result = await _score_leads(mock_context, None)

    assert result.success is True
    scored = mock_context.memory.read("scored_leads")

    assert scored[0]["icp_score"] == 70
    assert scored[1]["icp_score"] == 30


@pytest.mark.asyncio
async def test_route_node(mock_context):
    mock_context.memory.write(
        "scored_leads",
        [
            {"email": "ceo@enterprise.com", "icp_score": 85},
            {"email": "founder@techstartup.io", "icp_score": 60},
        ],
    )
    mock_context.memory.write("icp_score_threshold", 75)

    result = await _route_leads(mock_context, None)

    assert result.success is True
    routed = mock_context.memory.read("routed_leads")
    rejected = mock_context.memory.read("rejected_leads")

    assert len(routed) == 1
    assert routed[0]["email"] == "ceo@enterprise.com"

    assert len(rejected) == 1
    assert rejected[0]["email"] == "founder@techstartup.io"
