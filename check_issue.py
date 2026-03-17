import urllib.request
import json
import sys

req = urllib.request.Request("https://api.github.com/repos/adenhq/hive/issues/2741")
req.add_header("Accept", "application/vnd.github.v3+json")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Title: {data.get('title')}")
        assignees = data.get('assignees', [])
        print(f"Assignees: {[a.get('login') for a in assignees]}")
except Exception as e:
    print(f"Error: {e}")
