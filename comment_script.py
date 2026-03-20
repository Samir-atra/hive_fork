import os
import re

# Since there's no ~/.git-credentials, check if GITHUB_TOKEN is available directly.
token = os.environ.get('GITHUB_TOKEN')
if not token:
    raise RuntimeError("GITHUB_TOKEN is not set.")

from ghapi.all import GhApi

api = GhApi(owner='adenhq', repo='hive', token=token)

issue_author = 'AryanKansagara'

# Post comment
comment_body = f"""Hello @{issue_author}

I hope you are doing well,
I will start working on a PR, and please feel free to adapt and use my code in creating your pull request.

@RichardTang-Aden @bryanadenhq @TimothyZhang7

Please assign me to this issue, and I will create a pull request in a few minutes.

Kind regards
Samer"""

result = api.issues.create_comment(issue_number=2843, body=comment_body)
print(f"Comment posted: {result.html_url}")
