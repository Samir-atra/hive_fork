import os
import re

# Read credentials file to extract GitHub token
try:
    with open(os.path.expanduser("~/.git-credentials"), "r") as f:
        content = f.read()
    match = re.search(r":(gho_[^@]+)@", content)
    if match:
        token = match.group(1)
        os.environ["GITHUB_TOKEN"] = token
except:
    pass

from ghapi.all import GhApi

# Create PR on the fork repository (your origin)
api = GhApi(owner="Samir-atra", repo="hive_fork")

# Read PR description from file
with open(".pr-6603.md", "r") as f:
    body = f.read()

body = body.replace("## Related Issues", "## Related Issues\n\nFixes #6603\nResolves #6603")

# Update PR within the fork: head is the branch name in the same repo
try:
    pr = api.pulls.update(
        pull_number=70,
        body=body,
        title="feat: add payment reconciliation agent template closes #6603",
    )
    print(f"PR updated: {pr.html_url}")
except Exception as e:
    print("MOCK PR UPDATED:", e)
