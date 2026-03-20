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
    os.environ['GITHUB_TOKEN'] = token

    from ghapi.all import GhApi

    # Create PR on the fork repository (your origin)
    api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

    # Read PR description from file
    with open('.pr-2321.md', 'r') as f:
        body = f.read()

    pr = api.pulls.create(
        title="fix: CredentialUsageSpec Template Resolution Doesn't Work Correctly #2321",
        head="feat/CredentialUsageSpec-Template-Resolution-Doesnt-Work-Correctly-2321",
        base="main",
        body=body,
        maintainer_can_modify=True
    )

    print(f"PR created: {pr.html_url}")
except Exception as e:
    print(f"Warning: Could not open PR due to {str(e)}")
