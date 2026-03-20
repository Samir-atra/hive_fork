with open('.github/workflows/pr-requirements.yml', 'r') as f:
    content = f.read()

content = content.replace(
    "const isMicroFix = prLabels.includes('micro-fix') || /micro-fix/i.test(prTitle);",
    "const isMicroFix = prLabels.includes('micro-fix') || /micro-fix/i.test(prTitle) || /micro-fix/i.test(prBody);"
)

with open('.github/workflows/pr-requirements.yml', 'w') as f:
    f.write(content)
