import urllib.request
import json
req = urllib.request.Request("https://api.github.com/repos/adenhq/hive/issues/2579/comments")
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for c in data:
            print(f"[{c.get('user', {}).get('login')}]: {c.get('body')}")
except Exception as e:
    print(e)
