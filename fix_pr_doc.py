import os
import re
from ghapi.all import GhApi

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token (format: https://user:token@github.com)
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

api.pulls.update(pull_number=140, title="docs: update storage cache only after successful write")
print("Updated PR title")

api.issues.add_labels(issue_number=140, labels=["documentation"])
print("Added label")
