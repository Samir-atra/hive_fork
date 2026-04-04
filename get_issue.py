import urllib.request
import json

url = "https://api.github.com/repos/adenhq/hive/issues/6255"
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("TITLE:", data.get("title"))
        print("BODY:", data.get("body"))
        print("AUTHOR:", data.get("user", {}).get("login"))
except Exception as e:
    print("Error:", e)

url_comments = url + "/comments"
req_comments = urllib.request.Request(url_comments)
try:
    with urllib.request.urlopen(req_comments) as response:
        comments = json.loads(response.read().decode())
        for c in comments:
            print("COMMENT BY", c.get("user", {}).get("login"), ":", c.get("body"))
except Exception as e:
    print("Error getting comments:", e)
