import os
import re

with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
    content = f.read()

match = re.search(r':(gho_[^@]+)@', content)
token = match.group(1)

os.system(f"git push https://x-access-token:{token}@github.com/Samir-atra/hive_fork.git HEAD:feat/tui-deprecated-5809")
