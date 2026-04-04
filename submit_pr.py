import os
import re

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token (format: https://user:token@github.com)
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

# Create PR on the fork repository (your origin)
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# Read PR description from file
with open('.pr-5811.md', 'r') as f:
    body = f.read()

# Branch name
import subprocess
branch_name = subprocess.check_output(["git", "branch", "--show-current"]).decode().strip()

# Run git push directly
subprocess.run(["git", "push", "origin", branch_name, "-f"], check=True)

# Create PR within the fork: head is the branch name in the same repo
pr = api.pulls.create(
    title="fix: resolve misleading UI state for missing credentials in CredentialsModal on Windows",
    head=branch_name,  # Branch in Samir-atra/hive_fork
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
