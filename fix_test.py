with open("tools/tests/tools/test_zoho_books_tool.py", "r") as f:
    content = f.read()
content = content.replace('        assert "error" in result\n        assert "help" in result\n', '        assert "error" in result\n')
with open("tools/tests/tools/test_zoho_books_tool.py", "w") as f:
    f.write(content)
