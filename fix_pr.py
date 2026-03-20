import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# Get the PR
pr = api.pulls.get(pull_number=68)

# Add "Fixes #6649" to the body explicitly
body = pr.body or ""
if "Fixes #6649" not in body:
    body += "\n\nFixes #6649"

api.pulls.update(pull_number=68, body=body)
print("Updated PR body.")
