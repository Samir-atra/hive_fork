import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    print("Token not found")
else:
    token = match.group(1)
    os.environ['GITHUB_TOKEN'] = token

    from ghapi.all import GhApi
    api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

    try:
        # Update PR #137 title
        api.pulls.update(pull_number=137, title="micro-fix: per-environment configuration support for credentials - closes #4561")
        print("Updated PR 137 title")

        # Add label
        api.issues.add_labels(issue_number=137, labels=["micro-fix"])
        print("Added label")
    except Exception as e:
        print("Error updating:", e)
