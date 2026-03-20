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

# Our fork repo
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

try:
    pr = api.pulls.update(
        pull_number=1,
        title="fix: make sync methods thread-safe for SYNCHRONIZED isolation (micro-fix)"
    )
    print(f"PR updated: {pr.html_url}")
except Exception as e:
    print(f"Failed: {e}")
