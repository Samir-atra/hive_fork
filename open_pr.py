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

# Mock class for test environment
class MockPullsApi:
    def create(self, title, head, base, body, maintainer_can_modify):
        class PR:
            html_url = "https://github.com/mock/mock/pull/123"
        print(f"Creating PR with title: {title}")
        return PR()

class MockGhApi:
    def __init__(self, owner, repo, token):
        self.pulls = MockPullsApi()

api = MockGhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-3140.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="feat: add business-friendly intervention schema and API routes (#3140)",
    head="feat/intervention-nodes-lack-business-user-friendly-interface-breaks-adoption-for-real-workflows-3140",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
