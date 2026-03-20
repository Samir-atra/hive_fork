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

# Instead of updating the PR, we're just verifying we have it formatted exactly as the CI script expects.
print(body)
