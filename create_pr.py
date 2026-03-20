import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-2583.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="fix: enforce thread-safe read operations for SYNCHRONIZED isolation — closes #2583",
    head="feat/concurrency-violation-2583",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
