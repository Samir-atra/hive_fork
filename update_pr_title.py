import os
import re

# Since there's no ~/.git-credentials, check if GITHUB_TOKEN is available directly.
token = os.environ.get('GITHUB_TOKEN')
if not token:
    raise RuntimeError("GITHUB_TOKEN is not set.")

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

pr_number = 77
new_title = "fix: micro-fix mitigate HybridJudge multi-line parsing issue by removal — closes #2843"

result = api.pulls.update(pull_number=pr_number, title=new_title)
print(f"PR updated: {result.html_url}")
