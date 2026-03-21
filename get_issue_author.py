import json
import urllib.request
url = "https://api.github.com/repos/adenhq/hive/issues/3789"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
with urllib.request.urlopen(req) as response:
    issue = json.loads(response.read().decode())
    print("AUTHOR:", issue.get("user", {}).get("login"))
