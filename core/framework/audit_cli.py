"""CLI commands for audit trail."""

import argparse
import sys
from pathlib import Path

from framework.storage.audit_trail import AuditTrailStore
from framework.storage.backend import FileStorage


def register_audit_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register audit commands."""

    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit trail tools",
        description="Query decision timelines from execution logs.",
    )

    audit_parser.add_argument(
        "agent_path",
        type=str,
        help="Path to agent folder",
    )
    audit_parser.add_argument(
        "--run-id",
        type=str,
        help="Run ID to get timeline for",
    )
    audit_parser.add_argument(
        "--node",
        type=str,
        help="Node ID to get history for",
    )
    audit_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    audit_parser.set_defaults(func=cmd_audit)


def cmd_audit(args: argparse.Namespace) -> int:
    """Execute audit command."""
    agent_path = Path(args.agent_path)
    if not agent_path.exists():
        print(f"Error: Agent path {agent_path} does not exist", file=sys.stderr)
        return 1

    storage = FileStorage(agent_path)
    store = AuditTrailStore(storage)

    if args.run_id:
        timeline = store.get_execution_timeline(args.run_id)

        if args.json:
            import json
            from dataclasses import asdict

            print(json.dumps([asdict(e) for e in timeline], indent=2, default=str))
        else:
            print(f"Execution Timeline for Run: {args.run_id}")
            print("=" * 60)
            if not timeline:
                print("No timeline events found.")
            for event in timeline:
                print(f"[{event.timestamp}] Node: {event.node_id}")
                intent = event.details.get("intent", "N/A")
                print(f"  Intent: {intent}")
                success = event.details.get("success")
                success_str = "SUCCESS" if success else ("FAILED" if success is False else "N/A")
                print(f"  Status: {success_str}")
                print("-" * 60)

    elif args.node:
        decisions = store.query_decisions({"node_id": args.node})

        if args.json:
            import json

            print(json.dumps([d.model_dump() for d in decisions], indent=2, default=str))
        else:
            print(f"Decision History for Node: {args.node}")
            print("=" * 60)
            if not decisions:
                print("No decisions found.")
            for dec in decisions:
                print(f"[{dec.timestamp}] Intent: {dec.intent}")
                print(f"  Type: {dec.decision_type}")
                print(f"  Reasoning: {dec.reasoning}")
                print("-" * 60)
    else:
        print("Error: Must specify either --run-id or --node", file=sys.stderr)
        return 1

    return 0
