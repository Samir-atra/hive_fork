import os
import re

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token (format: https://user:token@github.com)
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-6103.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="docs: improve first-time developer onboarding with walkthrough and visual concepts",
    head="feat/improving-first-time-developer-onboarding-for-hive-6103",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
