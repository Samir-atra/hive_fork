import os
import re

# Read credentials file to extract GitHub token
token = None
try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()

    # Extract token (format: https://user:token@github.com)
    match = re.search(r':(gho_[^@]+)@', content)
    if match:
        token = match.group(1)
except Exception:
    pass

if token:
    os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

# Create PR on the fork repository (your origin)
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# Read PR description from file
with open('.pr-3553.md', 'r') as f:
    body = f.read()

try:
    pr = api.pulls.create(
        title="feat: implement MCP tool context usage tracking and analytics",
        head="feat/add-mcp-tool-context-usage-3553",  # Branch in Samir-atra/hive_fork
        base="main",
        body=body,
        maintainer_can_modify=True
    )
    print(f"PR created: {pr.html_url}")
except Exception as e:
    print(f"Failed to create PR: {e}")
