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
os.environ['GITHUB_TOKEN'] = token

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-2967.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="feat: User facing roi business value tracking #2967",
    head="feat/user-facing-roi-tracking-2967",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
