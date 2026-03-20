import os
os.environ['GITHUB_TOKEN'] = "ghp_fake_token"  # Dummy token or no token for public repo
import urllib.request
import json

req = urllib.request.Request("https://api.github.com/repos/adenhq/hive/issues/2579")
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("TITLE:", data.get('title'))
        print("BODY:", data.get('body'))
except Exception as e:
    print(e)
