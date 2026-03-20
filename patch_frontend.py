with open("core/frontend/src/api/types.ts", "r") as f:
    content = f.read()

content = content.replace(
    'is_clean: boolean;',
    'is_clean: boolean;\n  is_starred?: boolean;'
)

with open("core/frontend/src/api/types.ts", "w") as f:
    f.write(content)
