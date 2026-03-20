import os
import re

# Read credentials file to extract GitHub token
with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

# Extract token (format: https://user:token@github.com)
match = re.search(r':(gho_[^@]+)@', content)
if not match:
    raise RuntimeError("GitHub token not found in ~/.git-credentials")

token = match.group(1)
os.environ['GITHUB_TOKEN'] = token

from ghapi.all import GhApi

api = GhApi(owner='adenhq', repo='hive', token=token)

issue_author = "namrathamurarikar"
ISSUE_NUMBER = 3553

# Post comment
comment_body = f"""Hello @{issue_author}

I hope you are doing well,
I will start working on a PR, and please feel free to adapt and use my code in creating your pull request.

@RichardTang-Aden @bryanadenhq @TimothyZhang7

Please assign me to this issue, and I will create a pull request in a few minutes.

Kind regards
Samer"""

result = api.issues.create_comment(issue_number=ISSUE_NUMBER, body=comment_body)
print(f"Comment posted: {result.html_url}")
