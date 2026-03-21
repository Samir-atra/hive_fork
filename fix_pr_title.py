import os
import re

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

# Initialize GhApi on the fork where the PR was opened
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

# Retrieve open PRs for the branch
prs = api.pulls.list(head='Samir-atra:feat/add-rest-api-layer-3827', state='open')

if not prs:
    print("Could not find open PR for branch feat/add-rest-api-layer-3827")
else:
    pr_number = prs[0].number
    current_title = prs[0].title

    # Check if micro-fix is already in the title
    if 'micro-fix' not in current_title.lower():
        new_title = f"{current_title} micro-fix"
        api.pulls.update(pull_number=pr_number, title=new_title)
        print(f"Updated PR #{pr_number} title to: {new_title}")
    else:
        print(f"PR #{pr_number} title already contains micro-fix: {current_title}")
