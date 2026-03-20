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
api = GhApi(owner='adenhq', repo='hive', token=token)

try:
    # Try to assign the current issue (2371) to Samir-atra
    api.issues.add_assignees(issue_number=2371, assignees=['Samir-atra'])
    print("Assigned successfully!")
except Exception as e:
    print(f"Error: {e}")
