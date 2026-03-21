import threading

import pytest

from framework.graph.token_budget import TokenBudget, TokenBudgetExceededError


def test_token_budget_no_limit():
    budget = TokenBudget(limit=None)
    budget.record(100)
    budget.record(1000)
    assert budget.current == 1100


def test_token_budget_under_limit():
    budget = TokenBudget(limit=100)
    budget.record(50)
    budget.record(40)
    assert budget.current == 90


def test_token_budget_exceeds_limit():
    budget = TokenBudget(limit=100)
    budget.record(80)
    with pytest.raises(TokenBudgetExceededError) as exc_info:
        budget.record(30, node_id="test_node")

    assert exc_info.value.budget == 100
    assert exc_info.value.current == 110
    assert exc_info.value.node_id == "test_node"
    assert "test_node" in str(exc_info.value)


def test_token_budget_warning_log(caplog):
    import logging

    budget = TokenBudget(limit=100)
    with caplog.at_level(logging.WARNING):
        budget.record(79)
        assert "Token budget warning" not in caplog.text

        budget.record(1)  # exactly 80%
        assert "Token budget warning: 80/100 (80.0%) consumed" in caplog.text

        caplog.clear()
        budget.record(5)  # 85% - shouldn't log again
        assert "Token budget warning" not in caplog.text


def test_token_budget_thread_safe():
    budget = TokenBudget(limit=20000)

    def worker():
        for _ in range(100):
            budget.record(10)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert budget.current == 100 * 10 * 10
