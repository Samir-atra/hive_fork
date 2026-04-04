import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()
match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)

from ghapi.all import GhApi
api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)
prs = api.pulls.list()
for pr in prs:
    print(pr.number, pr.title)
