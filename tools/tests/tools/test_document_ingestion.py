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
        assert "not found" in result["error"].lower() or "not installed" in result["error"].lower()

    def test_docx_extract_file_not_found(self, docx_extract_fn, tmp_path: Path):
        """Reading non-existent DOCX returns error."""
        result = docx_extract_fn(path=str(tmp_path / "missing.docx"))
        assert "error" in result
        assert "not found" in result["error"].lower() or "not installed" in result["error"].lower()

    def test_xlsx_read_file_not_found(self, xlsx_read_fn, tmp_path: Path):
        """Reading non-existent XLSX returns error."""
        result = xlsx_read_fn(path=str(tmp_path / "missing.xlsx"))
        assert "error" in result
        assert "not found" in result["error"].lower() or "not installed" in result["error"].lower()

    def test_pdf_extract_text_pagination(self, pdf_extract_text_fn, tmp_path: Path):
        """Test PDF extraction limits characters correctly."""
        pypdf = pytest.importorskip("pypdf")

        pdf_file = tmp_path / "test.pdf"
        pdf_file.touch()

        mock_reader = MagicMock()
        mock_reader.is_encrypted = False

        page1 = MagicMock()
        page1.extract_text.return_value = "A" * 50000
        page2 = MagicMock()
        page2.extract_text.return_value = "B" * 50000

        mock_reader.pages = [page1, page2]

        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = pdf_extract_text_fn(path=str(pdf_file), start_page=1, max_chars=60000)

            assert "error" not in result
            assert len(result["pages"]) == 2
            assert result["pages"][0]["truncated"] is False
            assert len(result["pages"][0]["text"]) == 50000
            assert result["pages"][1]["truncated"] is True
            assert len(result["pages"][1]["text"]) == 10000
            assert result["next_page"] == 2
            assert result["next_start_char"] == 10000

            result2 = pdf_extract_text_fn(
                path=str(pdf_file),
                start_page=result["next_page"],
                start_char=result["next_start_char"],
                max_chars=60000,
            )
            assert len(result2["pages"]) == 1
            assert len(result2["pages"][0]["text"]) == 40000
            assert "next_page" not in result2

    def test_docx_extract_pagination(self, docx_extract_fn, tmp_path: Path):
        """Test DOCX extraction limits characters correctly."""
        docx = pytest.importorskip("docx")

        docx_file = tmp_path / "test.docx"
        docx_file.touch()

        mock_doc = MagicMock()
        p1 = MagicMock()
        p1.text = "A" * 50000
        p2 = MagicMock()
        p2.text = "B" * 50000

        mock_doc.paragraphs = [p1, p2]

        with patch("docx.Document", return_value=mock_doc):
            result = docx_extract_fn(path=str(docx_file), start_paragraph=1, max_chars=60000)

            assert "error" not in result
            assert len(result["paragraphs"]) == 2
            assert result["paragraphs"][0]["truncated"] is False
            assert len(result["paragraphs"][0]["text"]) == 50000
            assert result["paragraphs"][1]["truncated"] is True
            assert len(result["paragraphs"][1]["text"]) == 10000
            assert result["next_paragraph"] == 2
            assert result["next_start_char"] == 10000

            result2 = docx_extract_fn(
                path=str(docx_file),
                start_paragraph=result["next_paragraph"],
                start_char=result["next_start_char"],
                max_chars=60000,
            )
            assert len(result2["paragraphs"]) == 1
            assert len(result2["paragraphs"][0]["text"]) == 40000
            assert "next_paragraph" not in result2

    def test_xlsx_read_pagination(self, xlsx_read_fn, tmp_path: Path):
        """Test XLSX extraction limits rows correctly."""
        openpyxl = pytest.importorskip("openpyxl")

        xlsx_file = tmp_path / "test.xlsx"
        xlsx_file.touch()

        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]

        mock_ws = MagicMock()
        mock_ws.title = "Sheet1"
        mock_ws.max_row = 10

        def iter_rows_mock(min_row=1, values_only=True):
            rows = [
                ("A", "B", "C"),
                ("D", "E", "F"),
                ("G", "H", "I"),
            ]
            return rows[min_row - 1 :]

        mock_ws.iter_rows.side_effect = iter_rows_mock
        mock_wb.active = mock_ws
        mock_wb.__getitem__.return_value = mock_ws

        with patch("openpyxl.load_workbook", return_value=mock_wb):
            result = xlsx_read_fn(path=str(xlsx_file), max_rows=2)

            assert "error" not in result
            assert len(result["rows"]) == 2
            assert result["rows"][0]["values"] == ["A", "B", "C"]
            assert result["rows"][1]["values"] == ["D", "E", "F"]
            assert result["next_row"] == 3
