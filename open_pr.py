import os
import re

# Read credentials file to extract GitHub token
try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()

    # Extract token (format: https://user:token@github.com)
    match = re.search(r':(gho_[^@]+)@', content)
    if not match:
        raise RuntimeError("GitHub token not found in ~/.git-credentials")

    token = match.group(1)
except FileNotFoundError:
    token = None

if token:
    os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

# Create PR on the fork repository (your origin)
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# Read PR description from file
with open('.pr-3129.md', 'r') as f:
    body = f.read()

try:
    pr = api.pulls.create(
        title="feat: add AWS and Azure credential sources (#3129)",
        head="feat/feature-aws-secrets-manager-and-azure-key-vault-credential-sources-3129",
        base="main",
        body=body,
        maintainer_can_modify=True
    )
    print(f"PR created: {pr.html_url}")
except Exception as e:
    print(f"Failed to create PR: {e}")
