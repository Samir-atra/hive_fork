import urllib.request
import json
import sys

try:
    req = urllib.request.Request("https://api.github.com/repos/Samir-atra/hive_fork/issues/2294")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(data.get("title"))
        print(data.get("body"))
except Exception as e:
    print(e)
