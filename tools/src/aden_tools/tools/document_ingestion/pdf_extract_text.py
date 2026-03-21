"""PDF Extract Text tool."""

from pathlib import Path

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register PDF extraction tools with the MCP server."""

    @mcp.tool()
    def pdf_extract_text(
        path: str,
        start_page: int = 1,
        end_page: int | None = None,
        max_chars: int = 100000,
        start_char: int = 0,
    ) -> dict:
        """
        Extract text from a PDF document safely with pagination and length caps.

        Args:
            path: Path to the PDF file
            start_page: First page to extract (1-indexed)
            end_page: Last page to extract (inclusive, 1-indexed). Defaults to all.
            max_chars: Maximum characters to extract in this call (default 100,000).
                Use pagination if the document exceeds this limit.
            start_char: Character offset to start extracting from on the start_page.
                Used for pagination when a single page exceeds max_chars.

        Returns:
            Dict containing pages (with metadata), source metadata, next_page,
            and next_start_char token.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            return {"error": "pypdf not installed."}

        file_path = Path(path).resolve()
        if not file_path.exists():
            return {"error": f"PDF file not found: {path}"}
        if not file_path.is_file():
            return {"error": f"Not a file: {path}"}
        if file_path.suffix.lower() != ".pdf":
            return {"error": f"Not a PDF file: {path}"}

        try:
            reader = PdfReader(file_path)

            if reader.is_encrypted:
                return {"error": "Cannot read encrypted PDF."}

            total_pages = len(reader.pages)

            if start_page < 1:
                start_page = 1
            if start_page > total_pages:
                return {
                    "error": f"start_page {start_page} out of bounds (total pages: {total_pages})"
                }

            actual_end = min(end_page, total_pages) if end_page else total_pages
            if actual_end < start_page:
                return {"error": f"end_page {actual_end} before start_page {start_page}"}

            pages_data = []
            chars_extracted = 0
            truncated = False
            next_page = None
            next_start_char = 0

            for i in range(start_page - 1, actual_end):
                page_text = reader.pages[i].extract_text() or ""

                # Apply start_char offset only for the first page requested in this call
                if i == start_page - 1 and start_char > 0:
                    page_text = page_text[start_char:]
                else:
                    start_char = 0  # reset for subsequent pages

                if chars_extracted + len(page_text) > max_chars:
                    # Truncate this page to fit exactly up to max_chars
                    allowed_len = max_chars - chars_extracted
                    pages_data.append(
                        {
                            "page_number": i + 1,
                            "text": page_text[:allowed_len],
                            "truncated": True,
                        }
                    )
                    truncated = True
                    next_page = i + 1  # Next call should re-request this page
                    next_start_char = start_char + allowed_len
                    break

                pages_data.append(
                    {
                        "page_number": i + 1,
                        "text": page_text,
                        "truncated": False,
                    }
                )
                chars_extracted += len(page_text)

            result = {
                "pages": pages_data,
                "metadata": {
                    "source": str(file_path.name),
                    "total_pages": total_pages,
                    "chars_extracted": sum(len(p["text"]) for p in pages_data),
                },
            }
            if next_page is not None and next_page <= total_pages:
                result["next_page"] = next_page
                result["next_start_char"] = next_start_char
            elif not truncated and actual_end < total_pages:
                result["next_page"] = actual_end + 1
                result["next_start_char"] = 0

            return result

        except Exception as e:
            return {"error": f"Failed to extract text from PDF: {str(e)}"}
