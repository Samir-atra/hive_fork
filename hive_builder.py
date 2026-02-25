"""
Interactive Hive Agent Builder CLI.
Allows for step-by-step agent construction via the command line.
"""

import json
import os
import sys
from pathlib import Path

# Ensure core and tools/src are in the path
sys.path.append(os.path.abspath("core"))
sys.path.append(os.path.abspath("tools/src"))

from framework.mcp.agent_builder_server import (
    create_session,
    set_goal,
    add_node,
    add_edge,
    export_graph,
    validate_graph,
    add_mcp_server,
    list_mcp_tools,
)

def print_header(text):
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")

def main():
    print_header("🐝 Welcome to the Hive Interactive Builder")
    
    agent_name = input("Enter a name for your agent: ").strip() or "new_agent"
    session_json = create_session(name=agent_name)
    session_id = json.loads(session_json)["session_id"]
    print(f"✅ Session '{session_id}' started.")

    while True:
        print("\nWhat would you like to do?")
        print("1. Set Goal & success criteria")
        print("2. Register MCP Tool Servers")
        print("3. Add a Node")
        print("4. Add an Edge")
        print("5. Validate Graph")
        print("6. Export Agent & Exit")
        print("q. Quit without exporting")
        
        choice = input("\nChoice: ").strip().lower()
        
        if choice == '1':
            goal_id = input("Goal ID: ").strip()
            name = input("Goal Name: ").strip()
            desc = input("Goal Description: ").strip()
            
            # Simple success criteria for CLI
            criteria = []
            while True:
                c_desc = input("Add success criterion description (or empty to finish): ").strip()
                if not c_desc: break
                criteria.append({
                    "id": f"sc_{len(criteria)}",
                    "description": c_desc,
                    "metric": "manual",
                    "target": "pass",
                    "weight": 1.0
                })
            
            set_goal(goal_id, name, desc, json.dumps(criteria))
            print("✅ Goal set.")

        elif choice == '2':
            print("\nAvailable tool servers in project:")
            print(" - hive-tools (tools/mcp_server.py)")
            srv_name = input("Server name: ").strip() or "hive-tools"
            cwd = input("Working directory: ").strip() or "tools"
            
            # Register with PYTHONPATH support
            env = json.dumps({"PYTHONPATH": os.path.abspath("tools/src")})
            resp = add_mcp_server(
                name=srv_name,
                transport="stdio",
                command="python",
                args='["mcp_server.py", "--stdio"]',
                cwd=cwd,
                env=env
            )
            print(f"✅ Response: {resp}")

        elif choice == '3':
            node_id = input("Node ID: ").strip()
            name = input("Node Name: ").strip()
            desc = input("Description: ").strip()
            node_type = input("Type (llm_generate, llm_tool_use, router): ").strip() or "llm_generate"
            in_keys = input("Input Keys (JSON array, e.g. [\"input\"]): ").strip() or '["input"]'
            out_keys = input("Output Keys (JSON array): ").strip() or '["output"]'
            prompt = input("System Prompt: ").strip()
            tools = "[]"
            if node_type == "llm_tool_use":
                tools = input("Tool Names (JSON array): ").strip()
            
            resp = add_node(node_id, name, desc, node_type, in_keys, out_keys, prompt, tools)
            print(f"✅ Node Status: {resp}")

        elif choice == '4':
            edge_id = input("Edge ID: ").strip()
            source = input("Source Node ID: ").strip()
            target = input("Target Node ID: ").strip()
            cond = input("Condition (always, on_success, on_failure): ").strip() or "on_success"
            
            resp = add_edge(edge_id, source, target, cond)
            print(f"✅ Edge Status: {resp}")

        elif choice == '5':
            print("\n🔍 Validating...")
            print(validate_graph())

        elif choice == '6':
            print("\n💾 Exporting...")
            resp = export_graph()
            print(f"✅ Export Status: {resp}")
            print("\nBuild complete. Check the 'exports/' directory.")
            break

        elif choice == 'q':
            print("Bye!")
            break

if __name__ == "__main__":
    main()
