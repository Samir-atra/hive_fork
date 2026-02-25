#!/usr/bin/env python3
"""Minimal local runner to simulate the six-node GitLab skeleton flow.

This is a dry-run demonstration that doesn't require Hive runtime wiring.
It sequentially simulates the six nodes and prints a final summary.
"""

import json


def main():
    print("Starting GitLab Skeleton Demo Run (local, no external calls)")

    # Memory to carry outputs between steps
    memory = {}

    # Node 1: intake
    print("\n[Node] intake: Gather user intent")
    memory["task_request"] = {"action": "list_projects", "params": {"search": None}}
    print(f"Output: {memory['task_request']}")

    # Node 2: list_projects
    print("\n[Node] list_projects: List projects")
    memory["projects"] = [{"id": 1, "name": "demo-project"}]
    print(f"Output: {memory['projects']}")

    # Node 3: manage_issues
    print("\n[Node] manage_issues: List/Create issues")
    memory["issues"] = [{"id": 101, "title": "Demo issue"}]
    memory["created_issue"] = {"id": 101, "title": "Demo issue"}
    print(f"Output: issues={memory['issues']}, created_issue={memory['created_issue']}")

    # Node 4: manage_mr
    print("\n[Node] manage_mr: Get MR details")
    memory["merge_request"] = {"iid": 1, "title": "Demo MR"}
    print(f"Output: merge_request={memory['merge_request']}")

    # Node 5: manage_pipelines
    print("\n[Node] manage_pipelines: Trigger pipeline")
    memory["pipeline"] = {"id": 42, "status": "running"}
    print(f"Output: pipeline={memory['pipeline']}")

    # Node 6: respond
    print("\n[Node] respond: Present results")
    summary = (
        f"GitLab run complete. Projects={len(memory['projects'])}, "
        f"Issues={len(memory['issues'])}, MR={memory['merge_request']['iid']}, "
        f"Pipeline={memory['pipeline']['id']} status={memory['pipeline']['status']}"
    )
    memory["response"] = summary
    memory["done"] = True
    print("Output: ", memory["response"])

    # Final JSON-like summary
    result = {
        "done": memory["done"],
        "response": memory["response"],
    }
    print("\nFinal Result:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
