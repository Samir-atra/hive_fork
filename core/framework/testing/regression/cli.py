"""
CLI commands for agent regression and drift detection.
"""

import argparse
from datetime import datetime
from pathlib import Path
from framework.testing.regression.storage import RegressionStorage
from framework.testing.regression.schemas import RegressionBaseline
from framework.testing.test_storage import TestStorage

def register_regression_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register regression CLI commands."""

    # test-baseline
    baseline_parser = subparsers.add_parser(
        "test-baseline",
        help="Promote a test run to a performance baseline (golden result)",
    )
    baseline_parser.add_argument(
        "agent_path",
        help="Path to agent folder",
    )
    baseline_parser.add_argument(
        "--goal",
        "-g",
        required=True,
        help="Goal ID to create baseline for",
    )
    baseline_parser.set_defaults(func=cmd_test_baseline)

    # test-regress
    regress_parser = subparsers.add_parser(
        "test-regress",
        help="Run regression analysis against the latest baseline",
    )
    regress_parser.add_argument(
        "agent_path",
        help="Path to agent folder",
    )
    regress_parser.add_argument(
        "--goal",
        "-g",
        required=True,
        help="Goal ID to check",
    )
    regress_parser.set_defaults(func=cmd_test_regress)


def cmd_test_baseline(args: argparse.Namespace) -> int:
    """Promote the latest test run to a baseline."""
    agent_path = Path(args.agent_path)
    goal_id = args.goal
    
    # We need to find the latest test run for this goal
    # For MVP, we'll assume test results are stored in agent_path/.hive/testing
    storage_path = agent_path / ".hive" / "testing"
    test_storage = TestStorage(storage_path)
    reg_storage = RegressionStorage(storage_path)
    
    tests = test_storage.get_tests_by_goal(goal_id)
    if not tests:
        print(f"No tests found for goal {goal_id}")
        return 1
    
    # Calculate aggregate metrics from latest results
    total_passed = 0
    total_duration = 0
    test_outcomes = {}
    
    for test in tests:
        latest = test_storage.get_latest_result(test.id)
        if latest:
            if latest.passed:
                total_passed += 1
            total_duration += latest.duration_ms
            test_outcomes[test.id] = latest.actual_output
            
    if not test_outcomes:
        print(f"No test results found to promote for goal {goal_id}")
        return 1
        
    baseline = RegressionBaseline(
        goal_id=goal_id,
        baseline_id=f"base_{goal_id}_{int(datetime.now().timestamp())}",
        pass_rate=total_passed / len(tests),
        avg_duration_ms=total_duration / len(tests),
        test_outcomes=test_outcomes
    )
    
    reg_storage.save_baseline(baseline)
    print(f"Successfully promoted results to baseline for goal {goal_id}")
    print(f"  Pass Rate: {baseline.pass_rate:.1%}")
    print(f"  Avg Duration: {baseline.avg_duration_ms:.0f}ms")
    
    return 0


def cmd_test_regress(args: argparse.Namespace) -> int:
    """Perform regression analysis."""
    # Implementation will call RegressionComparator
    print("Regression analysis currently in implementation... (MVP CLI placeholder)")
    return 0
