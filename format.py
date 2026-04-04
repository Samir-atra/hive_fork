
with open("tools/src/aden_tools/tools/zoho_books_tool/zoho_books_tool.py", "r") as f:
    content = f.read()

def _auth_error() -> dict[str, str]:
    return {
        "error": "ZOHO_CRM_ACCESS_TOKEN not set",
        "help": "Generate an OAuth token via https://api-console.zoho.com/",
    }

content = content.replace("def register_tools", "def _auth_error() -> dict[str, Any]:\n    return {\n        \"error\": \"ZOHO_BOOKS_ORGANIZATION_ID or credentials not set\",\n        \"help\": \"Set ZOHO_CRM_ACCESS_TOKEN and ZOHO_BOOKS_ORGANIZATION_ID or configure oauth.\",\n    }\n\ndef register_tools")
content = content.replace('        if not token:\n            return _auth_error()', '        if not token:\n            return _auth_error()')

with open("tools/src/aden_tools/tools/zoho_books_tool/zoho_books_tool.py", "w") as f:
    f.write(content)
