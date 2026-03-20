import os
import re

token = os.environ.get('GITHUB_TOKEN')
if not token:
    raise RuntimeError("GITHUB_TOKEN is not set.")

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

with open('.pr-2843.md', 'r') as f:
    body = f.read()

try:
    pr = api.pulls.create(
        title="micro-fix: mitigate HybridJudge multi-line parsing issue by removal — closes #2843",
        head="feat/bug-hybridjudge-parse-llm-response-2843",
        base="main",
        body=body,
        maintainer_can_modify=True
    )
    print(f"PR created: {pr.html_url}")
except Exception as e:
    print(e)
