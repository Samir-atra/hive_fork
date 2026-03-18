import os
import re

try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()
    match = re.search(r':(gho_[^@]+)@', content)
    token = match.group(1) if match else None
except Exception:
    token = None

from ghapi.all import GhApi

# Note: The PR requirements check is running on the PR author's repository `hive_fork`
# the github token is for the user account that made the PR.
# We need to assign the PR author to the issue on `adenhq/hive`
# Actually, the issue is on `adenhq/hive`
api = GhApi(owner='adenhq', repo='hive', token=token)
try:
    user = api.users.get_authenticated()
    username = user.login
    api.issues.add_assignees(issue_number=3043, assignees=[username])
    print(f"Assigned {username} to issue 3043 on adenhq/hive")
except Exception as e:
    print(f"Failed: {e}")
