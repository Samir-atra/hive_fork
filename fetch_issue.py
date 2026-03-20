import os
import re
from ghapi.all import GhApi

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
api = GhApi(owner='adenhq', repo='hive', token=token)

issue = api.issues.get(issue_number=2579)
print("TITLE:", issue.title)
print("BODY:", issue.body)
print("\nCOMMENTS:")
comments = api.issues.list_comments(issue_number=2579)
for c in comments:
    print(f"[{c.user.login}]: {c.body}")
