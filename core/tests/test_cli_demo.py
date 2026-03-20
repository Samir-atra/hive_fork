import subprocess
import sys


def test_cmd_demo_runs_successfully():
    """Test that the hive demo command executes successfully."""
    # Run the demo command in a subprocess
    result = subprocess.run(
        [sys.executable, "-m", "framework", "demo"],
        capture_output=True,
        text=True,
    )

    # Assert it returns 0
    assert result.returncode == 0, f"Demo failed with output: {result.stderr}"

    # Assert expected output is present
    assert "Welcome to the Hive Demo Mode!" in result.stdout
    assert "Demo Execution Complete" in result.stdout
    assert "Success: " in result.stdout
