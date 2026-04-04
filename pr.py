import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-5809.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="docs: clarify that tui is deprecated and issue is obsolete - closes #5809",
    head="feat/tui-deprecated-5809",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
