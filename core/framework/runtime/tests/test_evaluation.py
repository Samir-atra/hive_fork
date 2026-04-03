import pytest
from datetime import datetime
from framework.runtime.core import Runtime
from framework.schemas.evaluation import EvaluationResult, FailureTaxonomy
from framework.storage.backend import FileStorage
from framework.schemas.run import Problem

@pytest.fixture
def tmp_storage(tmp_path):
    storage_path = tmp_path / "storage"
    return str(storage_path)

def test_evaluation_success(tmp_storage):
    runtime = Runtime(tmp_storage)
    run_id = runtime.start_run(goal_id="g1", goal_description="Test run")
    current_run = runtime.current_run

    runtime.end_run(success=True, narrative="All good")

    assert current_run is not None
    assert current_run.evaluation is not None
    assert isinstance(current_run.evaluation, EvaluationResult)
    assert current_run.evaluation.success is True
    assert current_run.evaluation.failure_category is None
    assert current_run.evaluation.cost == 0.0

def test_evaluation_failure_taxonomy(tmp_storage):
    runtime = Runtime(tmp_storage)
    run_id = runtime.start_run(goal_id="g2", goal_description="Test run with failure")
    current_run = runtime.current_run

    runtime.report_problem(severity="critical", description="Tool execution failed due to API error")

    runtime.end_run(success=False, narrative="Failed run")

    assert current_run is not None
    assert current_run.evaluation is not None
    assert current_run.evaluation.success is False
    assert current_run.evaluation.failure_category == FailureTaxonomy.TOOL_ERROR

def test_evaluation_timeout_taxonomy(tmp_storage):
    runtime = Runtime(tmp_storage)
    run_id = runtime.start_run(goal_id="g3", goal_description="Test run with timeout")
    current_run = runtime.current_run

    runtime.report_problem(severity="critical", description="Execution timeout after 30 seconds")

    runtime.end_run(success=False, narrative="Failed run")

    assert current_run is not None
    assert current_run.evaluation is not None
    assert current_run.evaluation.success is False
    assert current_run.evaluation.failure_category == FailureTaxonomy.TIMEOUT
