import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)

from ghapi.all import GhApi
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

prs = api.pulls.list(state='open')
for pr in prs:
    print(f"PR #{pr.number}: {pr.title} (Labels: {[l.name for l in pr.labels]})")
