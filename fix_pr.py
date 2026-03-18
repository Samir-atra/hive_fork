import os
import re
from ghapi.all import GhApi

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()
match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)
api.pulls.update(pull_number=40, title="feat: Implement Semantic Behavioral Diff and Analytics micro-fix")
api.issues.add_labels(issue_number=40, labels=['micro-fix'])
print("Updated PR 40")
