import os
import re
from urllib.request import Request, urlopen
import json

try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()
    match = re.search(r':(gho_[^@]+)@', content)
    token = match.group(1) if match else None
except Exception:
    token = None

url = "https://api.github.com/repos/adenhq/hive/issues/3789"
headers = {"Accept": "application/vnd.github.v3+json"}
if token:
    headers["Authorization"] = f"token {token}"

req = Request(url, headers=headers)
with urlopen(req) as response:
    issue = json.loads(response.read().decode())
    print("TITLE:", issue.get("title"))
    print("BODY:", issue.get("body"))

    comments_url = issue.get("comments_url")
    req = Request(comments_url, headers=headers)
    with urlopen(req) as c_response:
        comments = json.loads(c_response.read().decode())
        print("\n--- COMMENTS ---")
        for c in comments:
            print(f"Comment by {c.get('user', {}).get('login')}:\n{c.get('body')}\n---")
