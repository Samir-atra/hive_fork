"""Tests for document_ingestion tools (FastMCP)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.document_ingestion.docx_extract import register_tools as register_docx_extract
from aden_tools.tools.document_ingestion.pdf_extract_text import (
    register_tools as register_pdf_extract_text,
)
from aden_tools.tools.document_ingestion.xlsx_read import register_tools as register_xlsx_read


@pytest.fixture
def pdf_extract_text_fn(mcp: FastMCP):
    register_pdf_extract_text(mcp)
    return mcp._tool_manager._tools["pdf_extract_text"].fn


@pytest.fixture
def docx_extract_fn(mcp: FastMCP):
    register_docx_extract(mcp)
    return mcp._tool_manager._tools["docx_extract"].fn


@pytest.fixture
def xlsx_read_fn(mcp: FastMCP):
    register_xlsx_read(mcp)
    return mcp._tool_manager._tools["xlsx_read"].fn


class TestDocumentIngestionTools:
    """Tests for document_ingestion tools."""

    def test_pdf_extract_text_file_not_found(self, pdf_extract_text_fn, tmp_path: Path):
        """Reading non-existent PDF returns error."""
        result = pdf_extract_text_fn(path=str(tmp_path / "missing.pdf"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_docx_extract_file_not_found(self, docx_extract_fn, tmp_path: Path):
        """Reading non-existent DOCX returns error."""
        result = docx_extract_fn(path=str(tmp_path / "missing.docx"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_xlsx_read_file_not_found(self, xlsx_read_fn, tmp_path: Path):
        """Reading non-existent XLSX returns error."""
        result = xlsx_read_fn(path=str(tmp_path / "missing.xlsx"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch("pypdf.PdfReader")
    def test_pdf_extract_text_pagination(
        self, mock_pdf_reader, pdf_extract_text_fn, tmp_path: Path
    ):
        """Test PDF extraction limits characters correctly."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        mock_reader = MagicMock()
        mock_reader.is_encrypted = False

        # Create 2 pages
        page1 = MagicMock()
        page1.extract_text.return_value = "A" * 50000
        page2 = MagicMock()
        page2.extract_text.return_value = "B" * 50000

        mock_reader.pages = [page1, page2]
        mock_pdf_reader.return_value = mock_reader

        # Test max_chars=60000
        result = pdf_extract_text_fn(path=str(pdf_file), start_page=1, max_chars=60000)

        assert "error" not in result
        assert len(result["pages"]) == 2
        assert result["pages"][0]["truncated"] is False
        assert len(result["pages"][0]["text"]) == 50000
        assert result["pages"][1]["truncated"] is True
        assert len(result["pages"][1]["text"]) == 10000
        assert result["next_page"] == 2
        assert result["next_start_char"] == 10000

        # Test continuation
        result2 = pdf_extract_text_fn(
            path=str(pdf_file),
            start_page=result["next_page"],
            start_char=result["next_start_char"],
            max_chars=60000,
        )
        assert len(result2["pages"]) == 1
        assert len(result2["pages"][0]["text"]) == 40000
        assert "next_page" not in result2

    @patch("docx.Document")
    def test_docx_extract_pagination(self, mock_document_class, docx_extract_fn, tmp_path: Path):
        """Test DOCX extraction limits characters correctly."""
        docx_file = tmp_path / "test.docx"
        docx_file.touch()

        mock_doc = MagicMock()

        # Create 2 paragraphs
        p1 = MagicMock()
        p1.text = "A" * 50000
        p2 = MagicMock()
        p2.text = "B" * 50000

        mock_doc.paragraphs = [p1, p2]
        mock_document_class.return_value = mock_doc

        result = docx_extract_fn(path=str(docx_file), start_paragraph=1, max_chars=60000)

        assert "error" not in result
        assert len(result["paragraphs"]) == 2
        assert result["paragraphs"][0]["truncated"] is False
        assert len(result["paragraphs"][0]["text"]) == 50000
        assert result["paragraphs"][1]["truncated"] is True
        assert len(result["paragraphs"][1]["text"]) == 10000
        assert result["next_paragraph"] == 2
        assert result["next_start_char"] == 10000

        # Test continuation
        result2 = docx_extract_fn(
            path=str(docx_file),
            start_paragraph=result["next_paragraph"],
            start_char=result["next_start_char"],
            max_chars=60000,
        )
        assert len(result2["paragraphs"]) == 1
        assert len(result2["paragraphs"][0]["text"]) == 40000
        assert "next_paragraph" not in result2

    @patch("openpyxl.load_workbook")
    def test_xlsx_read_pagination(self, mock_load_workbook, xlsx_read_fn, tmp_path: Path):
        """Test XLSX extraction limits rows correctly."""
        xlsx_file = tmp_path / "test.xlsx"
        xlsx_file.touch()

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]

        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_ws.max_row = 10

        # 3 rows of data
        def iter_rows_mock(min_row=1, values_only=True):
            rows = [
                ("A", "B", "C"),
                ("D", "E", "F"),
                ("G", "H", "I"),
            ]
            # iter_rows is inclusive and 1-indexed, handle min_row
            return rows[min_row - 1 :]

        mock_ws.iter_rows.side_effect = iter_rows_mock
        mock_wb.active = mock_ws
        mock_wb.__getitem__.return_value = mock_ws

        mock_load_workbook.return_value = mock_wb

        # Extract 2 rows
        result = xlsx_read_fn(path=str(xlsx_file), max_rows=2)

        assert "error" not in result
        assert len(result["rows"]) == 2
        assert result["rows"][0]["values"] == ["A", "B", "C"]
        assert result["rows"][1]["values"] == ["D", "E", "F"]
        assert result["next_row"] == 3
