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

# Get open PRs for the branch
prs = api.pulls.list(state='open', head='Samir-atra:feat/bug-credentialstore-refresh-credential-returns-stale-token-2309-6211475347154111031')

if len(prs) > 0:
    pr = prs[0]
    pr_number = pr.number
    old_title = pr.title
    new_title = f"{old_title} [micro-fix]"
    api.pulls.update(pull_number=pr_number, title=new_title)
    print(f"Updated PR #{pr_number} title to: {new_title}")
else:
    print("No open PR found for this branch.")
