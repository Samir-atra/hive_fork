"""Tests for zoho_books_tool."""

from unittest.mock import patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.zoho_books_tool.zoho_books_tool import register_tools

ENV = {"ZOHO_CRM_ACCESS_TOKEN": "test-token", "ZOHO_BOOKS_ORGANIZATION_ID": "org-123"}


@pytest.fixture
def tool_fns(mcp: FastMCP):
    register_tools(mcp, credentials=None)
    tools = mcp._tool_manager._tools
    return {name: tools[name].fn for name in tools}


class TestZohoBooksGetContact:
    def test_missing_org(self, tool_fns):
        with patch.dict("os.environ", {"ZOHO_CRM_ACCESS_TOKEN": "test-token"}, clear=True):
            result = tool_fns["zoho_books_get_contact"](contact_id="123")
        assert "error" in result

    def test_successful_get(self, tool_fns):
        mock_resp = {"contact": {"contact_id": "123", "contact_name": "Smith"}}
        with (
            patch.dict("os.environ", ENV),
            patch("aden_tools.tools.zoho_books_tool.zoho_books_tool.httpx.get") as mock_get,
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_resp
            result = tool_fns["zoho_books_get_contact"](contact_id="123")
        assert result["contact"]["contact_name"] == "Smith"


class TestZohoBooksListInvoices:
    def test_successful_list(self, tool_fns):
        mock_resp = {"invoices": [{"invoice_id": "inv-1"}]}
        with (
            patch.dict("os.environ", ENV),
            patch("aden_tools.tools.zoho_books_tool.zoho_books_tool.httpx.get") as mock_get,
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_resp
            result = tool_fns["zoho_books_list_invoices"]()
        assert result["invoices"][0]["invoice_id"] == "inv-1"


class TestZohoBooksCreateInvoice:
    def test_successful_create(self, tool_fns):
        mock_resp = {"invoice": {"invoice_id": "inv-2"}}
        with (
            patch.dict("os.environ", ENV),
            patch("aden_tools.tools.zoho_books_tool.zoho_books_tool.httpx.post") as mock_post,
        ):
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = mock_resp
            result = tool_fns["zoho_books_create_invoice"](
                customer_id="cust-1", line_items=[{"item_id": "item-1"}]
            )
        assert result["invoice"]["invoice_id"] == "inv-2"
