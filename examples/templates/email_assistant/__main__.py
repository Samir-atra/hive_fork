"""CLI interface for Email Assistant."""

import asyncio
import os
import sys

from .agent import default_agent

async def main():
    max_emails = 10
    if len(sys.argv) > 1:
        try:
            max_emails = int(sys.argv[1])
        except ValueError:
            print("Argument must be an integer for max_emails.")
            sys.exit(1)

    print("==================================================")
    print(" Hive Email Assistant Agent                       ")
    print("==================================================")
    print(f"Max emails: {max_emails}")
    print("Starting agent...")

    # Load agent
    result = await default_agent.run({"max_emails": max_emails})
    
    print("\n--- Summary Report ---")
    if result.status == "success":
        report = result.state.get("summary_report", "No report available.")
        print(report)
    else:
        print(f"Agent failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
