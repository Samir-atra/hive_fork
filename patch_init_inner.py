with open("tools/src/aden_tools/tools/document_ingestion/__init__.py", "r") as f:
    content = f.read()

content = content.replace(
    "def register_tools(mcp: FastMCP, credentials=None) -> None:",
    "def register_tools(mcp: FastMCP) -> None:"
)
content = content.replace(
    '__all__ = ["register_tools", "register_pdf_extract_text", "register_docx_extract", "register_xlsx_read"]',
    '__all__ = [\n    "register_tools",\n    "register_pdf_extract_text",\n    "register_docx_extract",\n    "register_xlsx_read",\n]'
)

with open("tools/src/aden_tools/tools/document_ingestion/__init__.py", "w") as f:
    f.write(content)
