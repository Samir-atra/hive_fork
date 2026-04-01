import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# The PR number is 148 based on the log: "PR #148:"
api.pulls.update(pull_number=148, title="micro-fix: add graph_version to execution schemas")
print("PR title updated!")
