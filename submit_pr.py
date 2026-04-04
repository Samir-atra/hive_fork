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

with open('.pr-6175.md', 'r') as f:
    body = f.read()

try:
    pr = api.pulls.create(
        title="fix: resolve obsolete lint hygiene issue in aden client",
        head="feat/lint-hygiene-6175",
        base="main",
        body=body,
        maintainer_can_modify=True
    )
    print(f"PR created: {pr.html_url}")
except Exception as e:
    print(f"Failed to create PR: {e}")
