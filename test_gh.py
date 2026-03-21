import urllib.request
import json
req = urllib.request.Request("https://api.github.com/repos/Samir-atra/hive_fork/pulls?state=open")
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        for pr in data:
            print(f"PR #{pr['number']}: {pr['title']}")
except Exception as e:
    print(e)
