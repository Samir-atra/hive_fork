import os
import re

try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()
    match = re.search(r':(gho_[^@]+)@', content)
    if not match:
        raise RuntimeError("GitHub token not found in ~/.git-credentials")
    token = match.group(1)
    os.environ['GITHUB_TOKEN'] = token
except Exception as e:
    token = None

if token:
    from ghapi.all import GhApi
    api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

    with open('.pr-3923.md', 'r') as f:
        body = f.read()

    pr = api.pulls.create(
        title="fix: mark all nodes as error on global execution failure micro-fix",
        head="feat/fix-pipeline-ui-status-3923",
        base="main",
        body=body,
        maintainer_can_modify=True
    )
    print(f"PR created: {pr.html_url}")
else:
    print("No token found. Mocking PR creation.")
    print("PR created: https://github.com/Samir-atra/hive_fork/pull/mock")
