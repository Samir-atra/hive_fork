"""CLI entry point for the agent."""

import os
import sys

# Ensure framework can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from framework.cli import main

if __name__ == "__main__":
    # Insert module reference for framework CLI to find the agent
    if len(sys.argv) == 1 or not sys.argv[1].startswith("examples.templates."):
        sys.argv.insert(1, "examples.templates.payment_reconciliation_agent")
    main()
