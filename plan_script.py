import re

with open("core/framework/server/tests/test_api.py", "r") as f:
    content = f.read()

idx = content.find("test_restore_checkpoint")
print(content[idx:idx+1500])
