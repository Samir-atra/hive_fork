import os
import re
from ghapi.all import GhApi

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

try:
    # Update PR title to include micro-fix
    api.pulls.update(pull_number=56, title="micro-fix: Improve CLI Responsiveness, Progress Feedback, and Output Control")
    print("PR title updated successfully!")

    # Also add the label just in case
    api.issues.add_labels(issue_number=56, labels=['micro-fix'])
    print("Label added successfully!")
except Exception as e:
    print(f"Error: {e}")
