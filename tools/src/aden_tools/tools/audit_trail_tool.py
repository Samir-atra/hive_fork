"""MCP tools for querying the audit trail (decision timelines)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


def _parse_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def register_tools(mcp: FastMCP) -> None:
    """Register audit trail tools with the MCP server."""

    # Note: We duplicate some basic file loading logic here because MCP tools
    # shouldn't depend directly on the core framework storage classes to remain standalone.

    def _load_run(work_dir: Path, run_id: str) -> dict[str, Any] | None:
        run_path = work_dir / "runtime_logs" / "runs" / run_id / "run.json"
        if not run_path.exists():
            # In legacy structure, FileStorage writes to runs/
            run_path = work_dir / "runs" / f"{run_id}.json"
        if not run_path.exists():
            return None

        try:
            with open(run_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @mcp.tool()
    def get_execution_timeline(agent_work_dir: str, run_id: str) -> dict[str, Any]:
        """
        Get the complete decision timeline for a given run execution.

        Args:
            agent_work_dir: Path to the agent's working directory.
            run_id: The run ID to get the timeline for.

        Returns:
            A dictionary containing the timeline events.
        """
        work_dir = Path(agent_work_dir)
        run_data = _load_run(work_dir, run_id)

        if not run_data:
            return {"error": f"No run found with ID: {run_id}"}

        events = []
        for dec in run_data.get("decisions", []):
            decision_type = dec.get("decision_type", "custom")

            # Use evaluation success, otherwise outcome success
            was_successful = None
            if dec.get("evaluation"):
                eval_data = dec["evaluation"]
                was_successful = (
                    eval_data.get("goal_aligned", True)
                    and eval_data.get("outcome_quality", 0) > 0.5
                )
            elif dec.get("outcome"):
                was_successful = dec["outcome"].get("success")

            events.append(
                {
                    "timestamp": dec.get("timestamp"),
                    "event_type": "decision",
                    "node_id": dec.get("node_id"),
                    "decision_id": dec.get("id"),
                    "details": {
                        "intent": dec.get("intent"),
                        "decision_type": decision_type,
                        "chosen_option_id": dec.get("chosen_option_id"),
                        "reasoning": dec.get("reasoning"),
                        "success": was_successful,
                    },
                }
            )

        events.sort(key=lambda x: x.get("timestamp", ""))

        return {"run_id": run_id, "events": events}

    def _iter_all_runs(work_dir: Path):
        """Yield parsed run data from both modern and legacy directory structures."""
        # Check modern directory: runtime_logs/runs/<run_id>/run.json
        modern_runs_dir = work_dir / "runtime_logs" / "runs"
        if modern_runs_dir.exists():
            for run_dir in modern_runs_dir.iterdir():
                if run_dir.is_dir():
                    run_file = run_dir / "run.json"
                    if run_file.exists():
                        try:
                            with open(run_file, encoding="utf-8") as f:
                                yield json.load(f)
                        except (json.JSONDecodeError, OSError):
                            continue

        # Check legacy directory: runs/<run_id>.json
        legacy_runs_dir = work_dir / "runs"
        if legacy_runs_dir.exists():
            for run_file in legacy_runs_dir.glob("*.json"):
                try:
                    with open(run_file, encoding="utf-8") as f:
                        yield json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue

    @mcp.tool()
    def get_node_history(agent_work_dir: str, node_id: str) -> dict[str, Any]:
        """
        Get all decisions made by a specific node across all runs.

        Args:
            agent_work_dir: Path to the agent's working directory.
            node_id: The node ID to get history for.

        Returns:
            A dictionary containing the decisions made by the node.
        """
        work_dir = Path(agent_work_dir)

        history = []
        for run_data in _iter_all_runs(work_dir):
            for dec in run_data.get("decisions", []):
                if dec.get("node_id") == node_id:
                    history.append({"run_id": run_data.get("id"), "decision": dec})

        history.sort(key=lambda x: x["decision"].get("timestamp", ""))
        return {"node_id": node_id, "history": history}

    @mcp.tool()
    def query_audit_logs(
        agent_work_dir: str, node_id: str = "", start_time: str = "", end_time: str = ""
    ) -> dict[str, Any]:
        """
        Search decision history with filters.

        Args:
            agent_work_dir: Path to the agent's working directory.
            node_id: Filter by node ID.
            start_time: Filter by start time (ISO format).
            end_time: Filter by end time (ISO format).

        Returns:
            A dictionary containing matching decisions.
        """
        work_dir = Path(agent_work_dir)

        start_dt = _parse_datetime(start_time)
        end_dt = _parse_datetime(end_time)

        results = []
        for run_data in _iter_all_runs(work_dir):
            for dec in run_data.get("decisions", []):
                if node_id and dec.get("node_id") != node_id:
                    continue

                dec_dt = _parse_datetime(dec.get("timestamp"))
                if dec_dt:
                    if start_dt and dec_dt < start_dt:
                        continue
                    if end_dt and dec_dt > end_dt:
                        continue

                results.append({"run_id": run_data.get("id"), "decision": dec})

        results.sort(key=lambda x: x["decision"].get("timestamp", ""))
        return {"results": results}
