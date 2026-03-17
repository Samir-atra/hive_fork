import argparse
import json
from unittest.mock import MagicMock, patch

from framework.testing.cli import cmd_test_run


def test_cmd_test_run_success_report_parsing(tmp_path):
    # Setup test env
    agent_path = tmp_path / "my_agent"
    tests_dir = agent_path / "tests"
    tests_dir.mkdir(parents=True)

    # Create a dummy report.json in the tests dir
    report_file = tests_dir / ".report.json"
    dummy_report = {
        "tests": [
            {
                "nodeid": "test_foo.py::test_my_func",
                "outcome": "passed",
                "setup": {"duration": 0.01},
                "call": {"duration": 0.02},
                "teardown": {"duration": 0.005},
            },
            {
                "nodeid": "test_foo.py::test_fail_func",
                "outcome": "failed",
                "setup": {"duration": 0.01},
                "call": {
                    "duration": 0.02,
                    "outcome": "failed",
                    "crash": {"message": "assert False"},
                    "longrepr": "Traceback details...",
                },
                "teardown": {"duration": 0.005},
            },
        ]
    }

    # We don't want to actually run pytest in our test, so mock subprocess.run
    with patch("framework.testing.cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # Also, we mock TestStorage.save_result to capture what's saved
        with patch("framework.testing.test_storage.TestStorage") as mock_storage_class:
            mock_storage = MagicMock()
            mock_storage_class.return_value = mock_storage

            # Since the CLI expects to run subprocess and produce a report,
            # we must write the dummy report to the expected location right before it is parsed,
            # or just write it beforehand (which is fine since we mock subprocess.run anyway).
            with open(report_file, "w") as f:
                json.dump(dummy_report, f)

            args = argparse.Namespace(
                agent_path=str(agent_path), type="all", fail_fast=False, parallel=0
            )

            # cmd_test_run calls check_pytest_available, mock it to true
            with patch("framework.testing.cli._check_pytest_available", return_value=True):
                result_code = cmd_test_run(args)

            assert result_code == 0

            # Assert save_result was called twice
            assert mock_storage.save_result.call_count == 2

            # Check args for the first call (passed test)
            call_args_passed = mock_storage.save_result.call_args_list[0][0]
            assert call_args_passed[0] == "test_my_func"
            assert call_args_passed[1].passed is True
            # floating point math might give 34 instead of 35 sometimes: int(0.035 * 1000) -> 35
            assert call_args_passed[1].duration_ms in (34, 35)

            # Check args for the second call (failed test)
            call_args_failed = mock_storage.save_result.call_args_list[1][0]
            assert call_args_failed[0] == "test_fail_func"
            assert call_args_failed[1].passed is False
            assert call_args_failed[1].error_message == "assert False"
            assert call_args_failed[1].stack_trace == "Traceback details..."
