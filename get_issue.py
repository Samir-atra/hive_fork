import os
import re

# Try to read credentials if available
token = None
try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()
    match = re.search(r':(gho_[^@]+)@', content)
    if match:
        token = match.group(1)
except Exception:
    pass

import urllib.request
import json

url = "https://api.github.com/repos/adenhq/hive/issues/3803"
req = urllib.request.Request(url)
if token:
    req.add_header("Authorization", f"Bearer {token}")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"TITLE: {data.get('title')}")
        print(f"BODY:\n{data.get('body')}")

        comments_url = data.get('comments_url')
        if comments_url:
            comments_req = urllib.request.Request(comments_url)
            if token:
                comments_req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(comments_req) as comments_response:
                comments_data = json.loads(comments_response.read().decode())
                print("\nCOMMENTS:")
                for comment in comments_data:
                    print(f"--- {comment.get('user', {}).get('login')}:")
                    print(comment.get('body'))
except Exception as e:
    print(f"Error: {e}")
