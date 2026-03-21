"""
PDF Read Tool - Manage Accounting and Financial Operations.

Uses pypdf to read PDF documents and extract text content
along with metadata. Supports both local file paths and URLs.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP
from pypdf import PdfReader


def _parse_pdf_date(date_str: Any) -> str | Any:
    """
    Parse a PDF date string (e.g., 'D:20230501123456-05'00'') into ISO-8601 format.
    If parsing fails, returns the original string.
    """
    if not isinstance(date_str, str):
        date_str = str(date_str)

    if not date_str.startswith("D:"):
        return date_str

    # Extract digits and timezone info
    # Format: D:YYYYMMDDHHmmSS[+-]HH'mm' or D:YYYYMMDDHHmmSSZ
    # Some parts might be missing
    clean_str = date_str[2:].replace("'", "")

    # regex for standard pdf date: YYYYMMDDHHmmSS + timezone
    match = re.match(
        r"(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz]|[+-]\d{2,4})?", clean_str
    )
    if not match:
        return date_str

    year, month, day, hour, minute, second, tz = match.groups()

    month = month or "01"
    day = day or "01"
    hour = hour or "00"
    minute = minute or "00"
    second = second or "00"

    iso_str = f"{year}-{month}-{day}T{hour}:{minute}:{second}"

    if tz:
        if tz.upper() == "Z":
            iso_str += "Z"
        else:
            # tz might be like +0500 or -0500 or +05 or -05
            if len(tz) == 3:  # +05 -> +05:00
                iso_str += f"{tz}:00"
            elif len(tz) >= 5:  # +0500 -> +05:00
                iso_str += f"{tz[:3]}:{tz[3:5]}"
            else:
                iso_str += tz
    else:
        iso_str += "Z"

    return iso_str


def register_tools(mcp: FastMCP) -> None:
    """Register PDF read tools with the MCP server."""

    def parse_page_range(
        pages: str | None,
        total_pages: int,
        max_pages: int,
    ) -> dict[str, Any]:
        """
        Parse page range string into list of 0-indexed page numbers.

        Returns:
            Dict with either:
            - {"indices": [...], "truncated": bool, "requested_pages": int}
            - {"error": "..."} on invalid input
        """
        if pages is None or str(pages).strip().lower() == "all":
            requested_pages = total_pages
            limited = min(total_pages, max_pages)
            indices = list(range(limited))
            return {
                "indices": indices,
                "truncated": requested_pages > max_pages,
                "requested_pages": requested_pages,
            }

        try:
            # Strip whitespace
            pages = str(pages).replace(" ", "")

            requested_indices = []

            # Split by comma for mixed formats (e.g. "1, 2, 5-10")
            parts = pages.split(",")
            for part in parts:
                if not part:
                    continue
                # Handle single negative values
                if part.startswith("-") and "-" not in part[1:]:
                    page_num = int(part)
                    if abs(page_num) > total_pages:
                        return {
                            "error": f"Page {page_num} out of range. PDF has {total_pages} pages."
                        }
                    requested_indices.append(total_pages + page_num)
                # Handle ranges like 1-10
                elif "-" in part:
                    start_str, end_str = part.split("-", 1)
                    if not start_str:  # handled negative numbers above
                        return {"error": f"Invalid page range: {part}. Start must be provided."}

                    start, end = int(start_str), int(end_str)
                    if start > end:
                        return {
                            "error": f"Invalid page range: {part}. Start must be less than end."
                        }
                    if start < 1:
                        return {"error": f"Page numbers start at 1, got {start}."}
                    if end > total_pages:
                        return {"error": f"Page {end} out of range. PDF has {total_pages} pages."}

                    requested_indices.extend(list(range(start - 1, end)))
                else:  # single positive page
                    page_num = int(part)
                    if page_num < 1 or page_num > total_pages:
                        return {
                            "error": f"Page {page_num} out of range. PDF has {total_pages} pages."
                        }
                    requested_indices.append(page_num - 1)

            if not requested_indices:
                return {"error": f"Invalid page format: '{pages}'."}

            # Remove duplicates and preserve order
            seen = set()
            unique_indices = []
            for idx in requested_indices:
                if idx not in seen:
                    seen.add(idx)
                    unique_indices.append(idx)

            requested_pages = len(unique_indices)
            indices = unique_indices[:max_pages]

            return {
                "indices": indices,
                "truncated": requested_pages > max_pages,
                "requested_pages": requested_pages,
            }

        except ValueError as e:
            return {"error": f"Invalid page format: '{pages}'. {str(e)}"}

    @mcp.tool()
    def pdf_read(
        file_path: str,
        pages: str | None = None,
        max_pages: int = 100,
        include_metadata: bool = True,
    ) -> dict:
        """
        Read and extract text content from a PDF file.

        Returns text content with page markers and optional metadata.
        Use for reading PDFs, reports, documents, or any PDF file.
        Supports both local file paths and URLs.

        Args:
            file_path: Path or URL to the PDF file (local path, or http/https URL)
            pages: Page range - 'all'/None for all, '5' for single,
                '1-10' for range, '1,3,5' for specific
            max_pages: Maximum number of pages to process (1-1000, memory safety)
            include_metadata: Include PDF metadata (author, title, creation date, etc.)

        Returns:
            Dict with extracted text and metadata, or error dict
        """
        temp_file = None
        try:
            # Check if input is a URL
            is_url = file_path.startswith(("http://", "https://"))

            if is_url:
                # Download PDF from URL to temporary file
                try:
                    response = httpx.get(
                        file_path,
                        headers={"User-Agent": "AdenBot/1.0 (PDF Reader)"},
                        follow_redirects=True,
                        timeout=60.0,
                    )

                    if response.status_code != 200:
                        return {"error": f"Failed to download PDF: HTTP {response.status_code}"}

                    # Validate content-type
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/pdf" not in content_type:
                        return {
                            "error": (
                                f"URL does not point to a PDF file. Content-Type: {content_type}"
                            ),
                            "content_type": content_type,
                            "url": file_path,
                        }

                    # Save to temporary file
                    temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False)
                    temp_file.write(response.content)
                    temp_file.close()
                    path = Path(temp_file.name)

                except httpx.TimeoutException:
                    return {"error": "PDF download timed out"}
                except httpx.RequestError as e:
                    return {"error": f"Failed to download PDF: {str(e)}"}
            else:
                # Local file path
                path = Path(file_path).resolve()

            # Validate file exists
            if not path.exists():
                return {"error": f"PDF file not found: {file_path}"}

            if not path.is_file():
                return {"error": f"Not a file: {file_path}"}

            # Check extension
            if path.suffix.lower() != ".pdf":
                return {"error": f"Not a PDF file (expected .pdf): {file_path}"}

            # Validate max_pages
            if max_pages < 1:
                max_pages = 1
            elif max_pages > 1000:
                max_pages = 1000

            # Open and read PDF using context manager to ensure handles are closed
            with open(path, "rb") as f:
                reader = PdfReader(f)

                # Check for encryption
                if reader.is_encrypted:
                    return {"error": "Cannot read encrypted PDF. Password required."}

                total_pages = len(reader.pages)

                # Parse page range
                page_info = parse_page_range(pages, total_pages, max_pages)
                if "error" in page_info:
                    return page_info

                page_indices = page_info["indices"]

                # Extract text from pages
                content_parts = []
                for i in page_indices:
                    page_text = reader.pages[i].extract_text() or ""
                    content_parts.append(f"--- Page {i + 1} ---\n{page_text}")

                content = "\n\n".join(content_parts)

                result: dict[str, Any] = {
                    "path": str(path),
                    "name": path.name,
                    "total_pages": total_pages,
                    "pages_extracted": len(page_indices),
                    "content": content,
                    "char_count": len(content),
                }

                # Add warning for empty extraction
                # Strip dashes and newlines that are added for page markers
                stripped_content = re.sub(r"--- Page \d+ ---", "", content).strip()
                if len(stripped_content) == 0:
                    result["extracted_text_empty"] = True
                    result["extracted_text_warning"] = (
                        "Extracted text is empty. This may be a "
                        "scanned/image-only PDF requiring OCR."
                    )

                # Surface truncation information when requested pages exceed max_pages
                if page_info.get("truncated"):
                    requested = page_info.get("requested_pages", len(page_indices))
                    result["truncated"] = True
                    result["truncation_warning"] = (
                        f"Requested {requested} page(s), but max_pages={max_pages}. "
                        f"Only the first {len(page_indices)} page(s) were processed."
                    )

                # Add metadata if requested
                if include_metadata and reader.metadata:
                    meta = reader.metadata

                    created_date = meta.get("/CreationDate")
                    modified_date = meta.get("/ModDate")

                    result["metadata"] = {
                        "title": meta.get("/Title"),
                        "author": meta.get("/Author"),
                        "subject": meta.get("/Subject"),
                        "creator": meta.get("/Creator"),
                        "producer": meta.get("/Producer"),
                        "created": _parse_pdf_date(created_date) if created_date else None,
                        "modified": _parse_pdf_date(modified_date) if modified_date else None,
                    }

                return result

        except PermissionError:
            return {"error": f"Permission denied: {file_path}"}
        except Exception as e:
            return {"error": f"Failed to read PDF: {str(e)}"}
        finally:
            # Clean up temporary file if it was created
            if temp_file is not None:
                try:
                    Path(temp_file.name).unlink(missing_ok=True)
                except Exception:
                    pass  # Ignore cleanup errors
