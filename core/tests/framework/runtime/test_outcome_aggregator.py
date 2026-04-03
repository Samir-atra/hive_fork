import pytest

from framework.graph.goal import Goal, SuccessCriterion
from framework.runtime.outcome_aggregator import DecisionRecord, OutcomeAggregator
from framework.schemas.decision import Decision, Outcome


@pytest.fixture
def goal_with_criteria():
    return Goal(
        id="test-goal-1",
        name="Test Goal",
        description="A goal with different criteria types.",
        success_criteria=[
            SuccessCriterion(
                id="rate-criterion",
                description="Needs high success rate",
                metric="custom",
                type="success_rate",
                target="100%",
                weight=1.0,
            ),
            SuccessCriterion(
                id="struct-criterion",
                description="Needs specific output structure",
                metric="custom",
                type="structured_result",
                target={"key1": "val1", "key2": "val2"},
                weight=1.0,
            ),
            SuccessCriterion(
                id="state-criterion",
                description="Needs state change",
                metric="custom",
                type="state_change_check",
                target={"status": "completed"},
                weight=1.0,
            ),
        ],
    )


@pytest.fixture
def aggregator(goal_with_criteria):
    return OutcomeAggregator(goal=goal_with_criteria)


@pytest.mark.asyncio
async def test_evaluate_structured_result(aggregator):
    # Missing decision logic
    decision = Decision(
        id="d-1",
        node_id="n1",
        intent="produce structured output",
        active_constraints=["struct-criterion"],
    )
    # Failed outcome
    failed_outcome = Outcome(success=False, result={"key1": "wrong_val"})
    aggregator._decisions.append(
        DecisionRecord(stream_id="s1", execution_id="e1", decision=decision, outcome=failed_outcome)
    )

    status = await aggregator.evaluate_goal_progress()
    struct_status = status["criteria_status"]["struct-criterion"]
    assert struct_status["met"] is False
    assert struct_status["progress"] == 0.0

    # Successful outcome with correct structure
    success_outcome = Outcome(
        success=True, result={"key1": "val1", "key2": "val2", "extra": "ignored"}
    )
    aggregator._decisions.append(
        DecisionRecord(
            stream_id="s1", execution_id="e2", decision=decision, outcome=success_outcome
        )
    )

    status = await aggregator.evaluate_goal_progress()
    struct_status = status["criteria_status"]["struct-criterion"]
    assert struct_status["met"] is True
    assert struct_status["progress"] == 1.0


@pytest.mark.asyncio
async def test_evaluate_state_change_check(aggregator):
    decision = Decision(
        id="d-2", node_id="n1", intent="change some state", active_constraints=["state-criterion"]
    )
    # Success outcome but wrong state changes
    wrong_state_outcome = Outcome(success=True, state_changes={"status": "pending"})
    aggregator._decisions.append(
        DecisionRecord(
            stream_id="s1", execution_id="e3", decision=decision, outcome=wrong_state_outcome
        )
    )

    status = await aggregator.evaluate_goal_progress()
    state_status = status["criteria_status"]["state-criterion"]
    assert state_status["met"] is False
    assert state_status["progress"] == 0.0

    # Success outcome with correct state changes
    correct_state_outcome = Outcome(
        success=True, state_changes={"status": "completed", "other": "ignored"}
    )
    aggregator._decisions.append(
        DecisionRecord(
            stream_id="s1", execution_id="e4", decision=decision, outcome=correct_state_outcome
        )
    )

    status = await aggregator.evaluate_goal_progress()
    state_status = status["criteria_status"]["state-criterion"]
    assert state_status["met"] is True
    assert state_status["progress"] == 1.0
