import os, re
with open(os.path.expanduser("~/.git-credentials"), "r") as f:
    content = f.read()
match = re.search(r":(gho_[^@]+)@", content)
if not match:
    raise RuntimeError("GitHub token not found")
token = match.group(1)
os.environ["GITHUB_TOKEN"] = token
from ghapi.all import GhApi

api = GhApi(owner="adenhq", repo="hive", token=token)

issue_author = "UJJWALTHAKUR28"
try:
    api.issues.add_assignees(issue_number=2583, assignees=["Samir-atra"])
    print("Successfully assigned Samir-atra to issue #2583")
except Exception as e:
    print(f"Failed to assign user: {e}")
