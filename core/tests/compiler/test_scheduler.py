import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from compiler.scheduler import ConstraintAwareScheduler
from compiler.schemas import IRNode, WorkflowIR


def test_scheduler_topological_sort():
    ir = WorkflowIR(
        name="test_workflow",
        nodes=[
            IRNode(id="A", dependencies=[]),
            IRNode(id="B", dependencies=["A"]),
            IRNode(id="C", dependencies=["A"]),
            IRNode(id="D", dependencies=["B", "C"]),
        ],
    )

    scheduler = ConstraintAwareScheduler(max_parallelism=2)
    schedule = scheduler.schedule(ir)

    # D must come after B and C
    d_idx = schedule.order.index("D")
    b_idx = schedule.order.index("B")
    c_idx = schedule.order.index("C")
    assert d_idx > b_idx
    assert d_idx > c_idx

    # Waves should group B and C together due to parallelism=2
    assert ["A"] in schedule.waves
    assert {"B", "C"} in [set(w) for w in schedule.waves]
    assert ["D"] in schedule.waves


def test_scheduler_cycle_detection():
    ir = WorkflowIR(
        name="test_workflow",
        nodes=[
            IRNode(id="A", dependencies=["C"]),
            IRNode(id="B", dependencies=["A"]),
            IRNode(id="C", dependencies=["B"]),
        ],
    )

    scheduler = ConstraintAwareScheduler()
    with pytest.raises(ValueError, match="Cycle detected"):
        scheduler.schedule(ir)


def test_scheduler_parallelism_limits():
    ir = WorkflowIR(
        name="test_workflow",
        nodes=[
            IRNode(id="A", dependencies=[]),
            IRNode(id="B", dependencies=[]),
            IRNode(id="C", dependencies=[]),
            IRNode(id="D", dependencies=["A", "B", "C"]),
        ],
    )

    scheduler = ConstraintAwareScheduler(max_parallelism=2)
    schedule = scheduler.schedule(ir)

    # Waves should split A, B, C into two chunks due to max_parallelism=2
    assert len(schedule.waves[0]) == 2
    assert len(schedule.waves[1]) == 1
    assert schedule.waves[2] == ["D"]
