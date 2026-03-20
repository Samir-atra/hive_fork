import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from templates.payment_reconciliation_agent.agent import PaymentReconciliationAgent


@pytest.mark.asyncio
async def test_agent_initialization():
    agent = PaymentReconciliationAgent()
    assert agent is not None
    assert agent.entry_node == "extract_data"
