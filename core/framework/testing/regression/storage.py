"""
Storage backend for regression baselines and historical trends.
"""

import json
from pathlib import Path
from typing import Any

from framework.testing.regression.schemas import RegressionBaseline, RegressionResult
from framework.testing.test_storage import TestStorage


class RegressionStorage:
    """
    Handles persistence of golden baselines and regression analysis results.
    
    Structure:
    {base_path}/regression/
      baselines/{goal_id}/
        latest.json
        {timestamp}.json
      reports/{goal_id}/
        {timestamp}.json
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path) / "regression"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        (self.base_path / "baselines").mkdir(parents=True, exist_ok=True)
        (self.base_path / "reports").mkdir(parents=True, exist_ok=True)

    def save_baseline(self, baseline: RegressionBaseline) -> None:
        """Save a new performance baseline."""
        goal_dir = self.base_path / "baselines" / baseline.goal_id
        goal_dir.mkdir(parents=True, exist_ok=True)

        # Save with timestamp
        ts = baseline.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{baseline.baseline_id}.json"
        
        with open(goal_dir / filename, "w", encoding="utf-8") as f:
            f.write(baseline.model_dump_json(indent=2))
        
        # Link latest
        latest_path = goal_dir / "latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            f.write(baseline.model_dump_json(indent=2))

    def get_latest_baseline(self, goal_id: str) -> RegressionBaseline | None:
        """Retrieve the latest baseline for a goal."""
        latest_path = self.base_path / "baselines" / goal_id / "latest.json"
        if not latest_path.exists():
            return None
        with open(latest_path, encoding="utf-8") as f:
            return RegressionBaseline.model_validate_json(f.read())

    def save_regression_report(self, result: RegressionResult) -> None:
        """Save a regression analysis report."""
        report_dir = self.base_path / "reports" / result.goal_id
        report_dir.mkdir(parents=True, exist_ok=True)
        
        ts = result.timestamp.strftime("%Y%m%d_%H%M%S")
        with open(report_dir / f"{ts}.json", "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

    def get_history(self, goal_id: str, limit: int = 10) -> list[RegressionResult]:
        """Get historical regression results."""
        report_dir = self.base_path / "reports" / goal_id
        if not report_dir.exists():
            return []
        
        files = sorted(report_dir.glob("*.json"), reverse=True)[:limit]
        results = []
        for f in files:
            with open(f, encoding="utf-8") as file:
                results.append(RegressionResult.model_validate_json(file.read()))
        return results
