"""Document ingestion tools for PDF, DOCX, and XLSX."""

from fastmcp import FastMCP

from .docx_extract import register_tools as register_docx_extract
from .pdf_extract_text import register_tools as register_pdf_extract_text
from .xlsx_read import register_tools as register_xlsx_read


def register_tools(mcp: FastMCP) -> None:
    """Register all document ingestion tools with the MCP server."""
    register_pdf_extract_text(mcp)
    register_docx_extract(mcp)
    register_xlsx_read(mcp)


__all__ = [
    "register_tools",
    "register_pdf_extract_text",
    "register_docx_extract",
    "register_xlsx_read",
]
