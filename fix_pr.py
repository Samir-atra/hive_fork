import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)

from ghapi.all import GhApi

api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

try:
    pr = api.pulls.get(pull_number=75)
    body = pr.body or ""
    title = pr.title or ""
    print(f"Old Title: {title}")
    print(f"Old Body: {body}")

    new_body = f"Fixes #6613\n\n{body}"
    new_title = f"{title} - Fixes #6613"
    api.pulls.update(pull_number=75, body=new_body, title=new_title)
    print("Successfully updated PR 75")
except Exception as e:
    print(f"Error: {e}")
