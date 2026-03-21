"""Document ingestion tools for PDF, DOCX, and XLSX."""

from .docx_extract import register_tools as register_docx_extract
from .pdf_extract_text import register_tools as register_pdf_extract_text
from .xlsx_read import register_tools as register_xlsx_read

__all__ = ["register_pdf_extract_text", "register_docx_extract", "register_xlsx_read"]
