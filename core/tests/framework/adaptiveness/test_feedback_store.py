import pytest

from framework.adaptiveness.feedback_store import FeedbackStore


@pytest.fixture
def temp_feedback_store(tmp_path):
    # Override path before initialization
    original_path = FeedbackStore._store_path
    FeedbackStore._store_path = tmp_path / "test_feedback.json"
    FeedbackStore._instance = None

    store = FeedbackStore()

    yield store

    FeedbackStore._store_path = original_path
    FeedbackStore._instance = None


def test_feedback_store_singleton():
    store1 = FeedbackStore()
    store2 = FeedbackStore()
    assert store1 is store2


def test_add_and_get_feedback(temp_feedback_store):
    store = temp_feedback_store
    store.add_feedback("Test feedback 1")
    store.add_feedback("Test feedback 2", scope="agent_1")

    all_feedback = store.get_all_feedback()
    assert len(all_feedback) == 2
    assert all_feedback[0]["content"] == "Test feedback 1"
    assert all_feedback[0]["scope"] == "global"
    assert all_feedback[1]["content"] == "Test feedback 2"
    assert all_feedback[1]["scope"] == "agent_1"

    global_feedback = store.get_global_feedback()
    assert len(global_feedback) == 1
    assert global_feedback[0] == "Test feedback 1"
