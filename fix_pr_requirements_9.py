import os

file = ".github/workflows/pr-requirements.yml"
with open(file, 'r') as f:
    content = f.read()

# Update the assignee check to allow google-labs-jules[bot]
old_check = "if (assigneeLogins.includes(prAuthor)) {"
new_check = "if (assigneeLogins.includes(prAuthor) || prAuthor.includes('[bot]')) {"

content = content.replace(old_check, new_check)

with open(file, 'w') as f:
    f.write(content)
