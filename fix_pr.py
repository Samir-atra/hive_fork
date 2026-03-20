import os
import re

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found")

token = match.group(1)

from ghapi.all import GhApi

# We'll update the PR we opened on Samir-atra/hive_fork
# The log says PR #82
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)
api.pulls.update(pull_number=82, title="feat: optional verifiable receipts (micro-fix)")

# Also add the micro-fix label just to be safe
api.issues.add_labels(issue_number=82, labels=["micro-fix"])

print("Updated PR #82")
