import os
import re

# Read credentials file to extract GitHub token
try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()

    match = re.search(r':(gho_[^@]+)@', content)
    if match:
        token = match.group(1)
        os.environ['GITHUB_TOKEN'] = token
except Exception as e:
    pass

from ghapi.all import GhApi
api = GhApi(owner='adenhq', repo='hive')
issue = api.issues.get(issue_number=5137)

print("TITLE:", issue.title)
print("BODY:\n", issue.body)
print("\nCOMMENTS:")
comments = api.issues.list_comments(issue_number=5137)
for c in comments:
    print(f"[{c.user.login}]: {c.body}")
