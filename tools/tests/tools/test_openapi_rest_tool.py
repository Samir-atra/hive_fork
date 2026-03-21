import pytest
from httpx import Response
from fastmcp import FastMCP
from aden_tools.tools.openapi_rest_tool import register_tools as register_openapi_rest

class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        from httpx import Request
        req = Request(method, url)
        if url == "https://api.example.com/data":
            if headers and headers.get("Authorization") == "Bearer my_test_token":
                if method == "GET":
                    return Response(200, request=req, json={"success": True, "message": "GET successful"})
                if method == "POST" and json == {"name": "test"}:
                    return Response(201, request=req, json={"success": True, "message": "POST successful"})
            else:
                return Response(401, request=req, json={"error": "Unauthorized"})
        return Response(404, request=req, json={"error": "Not Found"})

@pytest.fixture
def mcp():
    return FastMCP("test_openapi")

@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("OPENAPI_API_KEY", "my_test_token")
    return None

def test_openapi_rest_tool_get(mcp, credentials, monkeypatch):
    monkeypatch.setattr("httpx.Client", lambda: MockClient())

    register_openapi_rest(mcp, credentials=credentials)
    openapi_request = mcp._tool_manager._tools["openapi_request"].fn

    result = openapi_request(
        method="GET",
        url="https://api.example.com/data",
    )

    assert result["status_code"] == 200
    assert result["data"]["success"] is True
    assert result["data"]["message"] == "GET successful"

def test_openapi_rest_tool_post(mcp, credentials, monkeypatch):
    monkeypatch.setattr("httpx.Client", lambda: MockClient())

    register_openapi_rest(mcp, credentials=credentials)
    openapi_request = mcp._tool_manager._tools["openapi_request"].fn

    result = openapi_request(
        method="POST",
        url="https://api.example.com/data",
        json_body={"name": "test"}
    )

    assert result["status_code"] == 201
    assert result["data"]["success"] is True
    assert result["data"]["message"] == "POST successful"
