#!/usr/bin/env python3
"""
Validate the GitLab assistant GraphSpec wiring embedded in exports/gitlab_assistant/graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adjust to repo root (hive_fork)

try:
    from exports.gitlab_assistant.graph import gitlab_graph
except Exception as e:
    print(f"ERROR: Could not import gitlab_graph: {e}")
    sys.exit(2)


def main():
    errors = gitlab_graph.validate()
    if errors:
        print("Graph validation errors:")
        for err in errors:
            print("-", err)
        sys.exit(1)
    print("Graph is valid.")


if __name__ == "__main__":
    main()
