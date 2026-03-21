import re

with open("core/framework/runner/runner.py", "r") as f:
    content = f.read()

if 'get("token_budget"' in content:
    print("load_agent_export has token_budget")
else:
    print("load_agent_export DOES NOT have token_budget")

if "agent_config and hasattr(agent_config, 'token_budget')" in content:
    print("_load_module_agent has token_budget")
else:
    print("_load_module_agent DOES NOT have token_budget")
