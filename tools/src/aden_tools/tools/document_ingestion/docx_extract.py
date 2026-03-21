"""DOCX Extract Text tool."""

from pathlib import Path

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register DOCX extraction tools with the MCP server."""

    @mcp.tool()
    def docx_extract(
        path: str,
        start_paragraph: int = 1,
        max_chars: int = 100000,
        start_char: int = 0,
    ) -> dict:
        """
        Extract text from a DOCX file safely with pagination and length caps.

        Args:
            path: Path to the DOCX file
            start_paragraph: First paragraph to extract (1-indexed)
            max_chars: Maximum characters to extract in this call (default 100,000).
                Use pagination if the document exceeds this limit.
            start_char: Character offset to start extracting from on the start_paragraph.
                Used for pagination when a single paragraph exceeds max_chars.

        Returns:
            Dict containing paragraphs, source metadata, next_paragraph,
            and next_start_char token.
        """
        try:
            from docx import Document
        except ImportError:
            return {"error": "python-docx not installed."}

        file_path = Path(path).resolve()
        if not file_path.exists():
            return {"error": f"DOCX file not found: {path}"}
        if not file_path.is_file():
            return {"error": f"Not a file: {path}"}
        if file_path.suffix.lower() != ".docx":
            return {"error": f"Not a DOCX file: {path}"}

        try:
            document = Document(file_path)
            paragraphs = document.paragraphs
            total_paragraphs = len(paragraphs)

            if start_paragraph < 1:
                start_paragraph = 1
            if start_paragraph > total_paragraphs:
                return {
                    "error": f"start_paragraph {start_paragraph} out of bounds "
                    f"(total paragraphs: {total_paragraphs})"
                }

            paragraphs_data = []
            chars_extracted = 0
            truncated = False
            next_paragraph = None
            next_start_char = 0

            for i in range(start_paragraph - 1, total_paragraphs):
                p_text = paragraphs[i].text

                # Apply start_char offset only for the first paragraph requested in this call
                if i == start_paragraph - 1 and start_char > 0:
                    p_text = p_text[start_char:]
                else:
                    start_char = 0

                if chars_extracted + len(p_text) > max_chars:
                    allowed_len = max_chars - chars_extracted
                    paragraphs_data.append(
                        {
                            "index": i + 1,
                            "text": p_text[:allowed_len],
                            "truncated": True,
                        }
                    )
                    truncated = True
                    next_paragraph = i + 1  # Request same paragraph next time
                    next_start_char = start_char + allowed_len
                    break

                paragraphs_data.append(
                    {
                        "index": i + 1,
                        "text": p_text,
                        "truncated": False,
                    }
                )
                chars_extracted += len(p_text)

            result = {
                "paragraphs": paragraphs_data,
                "metadata": {
                    "source": str(file_path.name),
                    "total_paragraphs": total_paragraphs,
                    "chars_extracted": sum(len(p["text"]) for p in paragraphs_data),
                },
            }
            if next_paragraph is not None and next_paragraph <= total_paragraphs:
                result["next_paragraph"] = next_paragraph
                result["next_start_char"] = next_start_char
            elif not truncated and start_paragraph - 1 + len(paragraphs_data) < total_paragraphs:
                result["next_paragraph"] = start_paragraph + len(paragraphs_data)
                result["next_start_char"] = 0

            return result

        except Exception as e:
            return {"error": f"Failed to extract text from DOCX: {str(e)}"}
