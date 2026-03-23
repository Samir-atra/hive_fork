import re

with open("core/framework/graph/conversation.py") as f:
    code = f.read()

m = re.search(r'def add_user_message\(', code)
if m:
    print("Found add_user_message at", m.start())
    lines = code[m.start()-50:m.end()+50].splitlines()
    for l in lines:
        print(l)
else:
    print("Not found")
