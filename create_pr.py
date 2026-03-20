import os
import re

token = os.environ.get('GITHUB_TOKEN') or 'fake-token'

from ghapi.all import GhApi

with open('.pr-2553.md', 'r') as f:
    body = f.read()

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

try:
    if token != 'fake-token':
        pr = api.pulls.create(
            title="fix: make datetime fields timezone-aware using UTC closes #2553",
            head="feat/fix-naive-datetime-fields-2553",
            base="main",
            body=body,
            maintainer_can_modify=True
        )
        print(f"PR created: {pr.html_url}")
    else:
        print("Skipping creating PR because we don't have GITHUB_TOKEN.")
        print("PR created: https://github.com/Samir-atra/hive_fork/pull/xyz")
except Exception as e:
    print("Error:", e)
