import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='adenhq', repo='hive', token=token)

issue_author = "Samir-atra" # Looking at the curl output, but wait, let me just fetch it properly

issue = api.issues.get(issue_number=5809)
issue_author = issue.user.login

comment_body = f"""Hello @{issue_author}

I hope you are doing well,
I will start working on a PR, and please feel free to adapt and use my code in creating your pull request.

@RichardTang-Aden @bryanadenhq @TimothyZhang7

Please assign me to this issue, and I will create a pull request in a few minutes.

Kind regards
Samer"""

result = api.issues.create_comment(issue_number=5809, body=comment_body)
print(f"Comment posted: {result.html_url}")
