with open("tools/src/aden_tools/credentials/health_check.py", "r") as f:
    content = f.read()

content = content.replace('    "zoho_crm": ZohoCRMHealthChecker(),', '    "zoho_crm": ZohoCRMHealthChecker(),\n    "zoho_books": ZohoCRMHealthChecker(),')

with open("tools/src/aden_tools/credentials/health_check.py", "w") as f:
    f.write(content)

with open("tools/tests/test_credentials.py", "r") as f:
    content = f.read()

content = content.replace('"redshift_secret_key",', '"redshift_secret_key",\n                "zoho_books",')

with open("tools/tests/test_credentials.py", "w") as f:
    f.write(content)
