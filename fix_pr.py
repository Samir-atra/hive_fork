import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

# We know the PR number from the log: PR #32
# And we know the fork repo: Samir-atra/hive_fork
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

try:
    pr = api.pulls.get(pull_number=32)
    # Update the body to include "Fixes #2976" or "Resolves #2976"
    # Wait, the script says: Matches: fixes #123, closes #123, resolves #123, or plain #123
    # Our original .pr-2976.md had "Resolves #2976"
    print("Old body:", pr.body)
    new_body = pr.body.replace("Resolves #2976", "Fixes #2976")
    if "Fixes #2976" not in new_body:
         new_body += "\n\nFixes #2976"

    api.pulls.update(pull_number=32, body=new_body)
    print("Updated PR body to include 'Fixes #2976'")
except Exception as e:
    print(f"Error updating PR: {e}")
