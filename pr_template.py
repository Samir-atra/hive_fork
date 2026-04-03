# Post comment
import os
import re
import urllib.request
import json

# Setup ghapi
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='adenhq', repo='hive', token=token)

issue_author = 'girikization'
comment_body = f"""Hello @{issue_author}

I hope you are doing well,
I will start working on a PR, and please feel free to adapt and use my code in creating your pull request.

@RichardTang-Aden @bryanadenhq @TimothyZhang7

Please assign me to this issue, and I will create a pull request in a few minutes.

Kind regards
Samer"""

try:
    result = api.issues.create_comment(issue_number=5640, body=comment_body)
    print(f"Comment posted: {result.html_url}")
except Exception as e:
    print(f"Failed to post comment: {e}")
