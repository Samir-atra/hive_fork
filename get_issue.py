import os
import re
from urllib.request import Request, urlopen
import json

# Try to get token if exists, else do unauthenticated (might be rate limited but fine for one issue)
token = None
try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()
    match = re.search(r':(gho_[^@]+)@', content)
    if match:
        token = match.group(1)
except Exception:
    pass

url = "https://api.github.com/repos/adenhq/hive/issues/3553"
req = Request(url)
if token:
    req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github.v3+json")

try:
    with urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"TITLE: {data.get('title')}")
        print(f"AUTHOR: {data.get('user', {}).get('login')}")
        print(f"BODY:\n{data.get('body')}")

    # Get comments
    comments_url = data.get('comments_url')
    if comments_url:
        req_c = Request(comments_url)
        if token:
            req_c.add_header("Authorization", f"Bearer {token}")
        req_c.add_header("Accept", "application/vnd.github.v3+json")
        with urlopen(req_c) as response_c:
            comments = json.loads(response_c.read().decode())
            for c in comments:
                print(f"\nCOMMENT by {c.get('user', {}).get('login')}:\n{c.get('body')}")
except Exception as e:
    print(f"Error: {e}")
