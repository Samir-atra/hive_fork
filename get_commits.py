import urllib.request
import json
import sys

try:
    req = urllib.request.Request("https://api.github.com/repos/adenhq/hive/issues/2294/events")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(e)
