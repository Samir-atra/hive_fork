"""
Tests for Pinecone vector database tool.

Covers:
- _PineconeClient methods (list_indexes, create_index, query_vectors, etc.)
- Error handling (401, 403, 404, 429, 500, timeout)
- Credential retrieval (CredentialStoreAdapter vs env var)
- All 12 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from aden_tools.tools.pinecone_tool.pinecone_tool import (
    PINECONE_API_BASE,
    _PineconeClient,
    register_tools,
)


class TestPineconeClient:
    def setup_method(self):
        self.client = _PineconeClient("test-api-key")

    def test_headers(self):
        headers = self.client._headers
        assert headers["Api-Key"] == "test-api-key"
        assert headers["Content-Type"] == "application/json"

    def test_handle_response_success(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"indexes": []}
        assert self.client._handle_response(response) == {"indexes": []}

    def test_handle_response_201(self):
        response = MagicMock()
        response.status_code = 201
        response.json.return_value = {"name": "test-index"}
        assert self.client._handle_response(response) == {"name": "test-index"}

    @pytest.mark.parametrize(
        "status_code,expected_substring",
        [
            (401, "Invalid or expired"),
            (403, "Insufficient permissions"),
            (404, "not found"),
            (429, "Rate limit"),
            (500, "server error"),
        ],
    )
    def test_handle_response_errors(self, status_code, expected_substring):
        response = MagicMock()
        response.status_code = status_code
        result = self.client._handle_response(response)
        assert "error" in result
        assert expected_substring in result["error"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_list_indexes(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "indexes": [
                {
                    "name": "test-index",
                    "dimension": 1536,
                    "metric": "cosine",
                    "host": "test-index.svc.pinecone.io",
                    "status": {"ready": True},
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.client.list_indexes()

        mock_get.assert_called_once_with(
            f"{PINECONE_API_BASE}/indexes",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert "indexes" in result
        assert len(result["indexes"]) == 1

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_create_index(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "new-index",
            "dimension": 1536,
            "metric": "cosine",
            "host": "new-index.svc.pinecone.io",
        }
        mock_post.return_value = mock_response

        self.client.create_index("new-index", 1536)

        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["name"] == "new-index"
        assert call_json["dimension"] == 1536
        assert call_json["metric"] == "cosine"
        assert "serverless" in call_json["spec"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_create_index_with_custom_spec(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "custom-index"}
        mock_post.return_value = mock_response

        custom_spec = {"pod": {"environment": "us-west1-gcp", "replicas": 2}}
        self.client.create_index("custom-index", 768, spec=custom_spec)

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["spec"] == custom_spec

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_describe_index(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test-index",
            "dimension": 1536,
            "metric": "cosine",
            "host": "test-index.svc.pinecone.io",
            "status": {"ready": True},
        }
        mock_get.return_value = mock_response

        result = self.client.describe_index("test-index")

        mock_get.assert_called_once_with(
            f"{PINECONE_API_BASE}/indexes/test-index",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert result["name"] == "test-index"

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.delete")
    def test_delete_index(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_delete.return_value = mock_response

        self.client.delete_index("test-index")

        mock_delete.assert_called_once_with(
            f"{PINECONE_API_BASE}/indexes/test-index",
            headers=self.client._headers,
            timeout=30.0,
        )

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_vectors(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"upsertedCount": 2}
        mock_post.return_value = mock_response

        vectors = [
            {"id": "doc1", "values": [0.1, 0.2, 0.3]},
            {"id": "doc2", "values": [0.4, 0.5, 0.6]},
        ]
        result = self.client.upsert_vectors("test-index.svc.pinecone.io", vectors)

        mock_post.assert_called_once_with(
            "https://test-index.svc.pinecone.io/vectors/upsert",
            headers=self.client._headers,
            json={"vectors": vectors},
            timeout=60.0,
        )
        assert result["upsertedCount"] == 2

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_vectors_with_namespace(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"upsertedCount": 1}
        mock_post.return_value = mock_response

        vectors = [{"id": "doc1", "values": [0.1, 0.2]}]
        self.client.upsert_vectors("test-index.svc.pinecone.io", vectors, namespace="production")

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["namespace"] == "production"

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_query_vectors(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {"id": "doc1", "score": 0.95, "metadata": {"title": "Doc 1"}},
                {"id": "doc2", "score": 0.85, "metadata": {"title": "Doc 2"}},
            ],
            "namespace": "",
        }
        mock_post.return_value = mock_response

        result = self.client.query_vectors(
            "test-index.svc.pinecone.io",
            vector=[0.1, 0.2, 0.3],
            top_k=5,
        )

        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["vector"] == [0.1, 0.2, 0.3]
        assert call_json["top_k"] == 5
        assert "matches" in result

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_query_vectors_by_id(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"matches": []}
        mock_post.return_value = mock_response

        self.client.query_vectors(
            "test-index.svc.pinecone.io",
            id="doc1",
            top_k=10,
        )

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["id"] == "doc1"
        assert "vector" not in call_json

    def test_query_vectors_no_vector_or_id(self):
        result = self.client.query_vectors("test-index.svc.pinecone.io")
        assert "error" in result
        assert "Either 'vector' or 'id'" in result["error"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_fetch_vectors(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vectors": {
                "doc1": {"id": "doc1", "values": [0.1, 0.2], "metadata": {}},
            },
            "namespace": "",
        }
        mock_get.return_value = mock_response

        self.client.fetch_vectors("test-index.svc.pinecone.io", ["doc1"])

        mock_get.assert_called_once()
        call_params = mock_get.call_args.kwargs["params"]
        assert call_params["ids"] == ["doc1"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_delete_vectors_by_ids(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.client.delete_vectors("test-index.svc.pinecone.io", ids=["doc1", "doc2"])

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["ids"] == ["doc1", "doc2"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_delete_vectors_delete_all(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.client.delete_vectors("test-index.svc.pinecone.io", delete_all=True, namespace="test")

        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["deleteAll"] is True
        assert call_json["namespace"] == "test"

    def test_delete_vectors_no_params(self):
        result = self.client.delete_vectors("test-index.svc.pinecone.io")
        assert "error" in result

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_records(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        records = [{"_id": "doc1", "title": "Test Document"}]
        self.client.upsert_records("test-index.svc.pinecone.io", records, namespace="docs")

        mock_post.assert_called_once_with(
            "https://test-index.svc.pinecone.io/records/upsert",
            headers=self.client._headers,
            json={"records": records, "namespace": "docs"},
            timeout=60.0,
        )

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_search_records(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {"hits": [{"_id": "doc1", "_score": 0.95, "fields": {"title": "Test"}}]}
        }
        mock_post.return_value = mock_response

        self.client.search_records(
            "test-index.svc.pinecone.io",
            query={"text": "search query"},
            top_k=5,
        )

        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["query"] == {"text": "search query"}
        assert call_json["top_k"] == 5

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_list_namespaces(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "namespaces": {
                "": {"vectorCount": 100},
                "production": {"vectorCount": 500},
            }
        }
        mock_get.return_value = mock_response

        result = self.client.list_namespaces("test-index.svc.pinecone.io")

        mock_get.assert_called_once_with(
            "https://test-index.svc.pinecone.io/namespaces",
            headers=self.client._headers,
            timeout=30.0,
        )
        assert "namespaces" in result

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.delete")
    def test_delete_namespace(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        self.client.delete_namespace("test-index.svc.pinecone.io", "old-namespace")

        mock_delete.assert_called_once_with(
            "https://test-index.svc.pinecone.io/namespaces/old-namespace",
            headers=self.client._headers,
            timeout=30.0,
        )


class TestToolRegistration:
    def _get_tool_fn(self, mcp_mock, tool_name):
        """Extract a registered tool function by name from mcp.tool() calls."""
        for call in mcp_mock.tool.return_value.call_args_list:
            fn = call[0][0]
            if fn.__name__ == tool_name:
                return fn
        raise ValueError(f"Tool '{tool_name}' not found in registered tools")

    def test_register_tools_registers_all_tools(self):
        mcp = MagicMock()
        mcp.tool.return_value = lambda fn: fn
        register_tools(mcp)
        assert mcp.tool.call_count == 12

    def test_no_credentials_returns_error(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        with patch.dict("os.environ", {}, clear=True):
            register_tools(mcp, credentials=None)

        list_fn = next(fn for fn in registered_fns if fn.__name__ == "pinecone_list_indexes")
        result = list_fn()
        assert "error" in result
        assert "not configured" in result["error"]

    def test_credentials_from_credential_manager(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        cred_manager = MagicMock()
        cred_manager.get.return_value = "test-api-key"

        register_tools(mcp, credentials=cred_manager)

        list_fn = next(fn for fn in registered_fns if fn.__name__ == "pinecone_list_indexes")

        with patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"indexes": []}
            mock_get.return_value = mock_response

            result = list_fn()

        cred_manager.get.assert_called_with("pinecone")
        assert result["success"] is True

    def test_credentials_from_env_var(self):
        mcp = MagicMock()
        registered_fns = []
        mcp.tool.return_value = lambda fn: registered_fns.append(fn) or fn

        register_tools(mcp, credentials=None)

        list_fn = next(fn for fn in registered_fns if fn.__name__ == "pinecone_list_indexes")

        with (
            patch.dict("os.environ", {"PINECONE_API_KEY": "env-api-key"}),
            patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get") as mock_get,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"indexes": []}
            mock_get.return_value = mock_response

            result = list_fn()

        assert result["success"] is True
        call_headers = mock_get.call_args.kwargs["headers"]
        assert call_headers["Api-Key"] == "env-api-key"


class TestIndexTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-key"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_list_indexes(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "indexes": [
                        {
                            "name": "test-index",
                            "dimension": 1536,
                            "metric": "cosine",
                            "host": "test.svc.pinecone.io",
                            "status": {"ready": True},
                        }
                    ]
                }
            ),
        )
        result = self._fn("pinecone_list_indexes")()
        assert result["success"] is True
        assert result["count"] == 1

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_create_index(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(
                return_value={
                    "name": "new-index",
                    "dimension": 1536,
                    "metric": "cosine",
                    "host": "new.svc.pinecone.io",
                }
            ),
        )
        result = self._fn("pinecone_create_index")(
            name="new-index", dimension=1536, metric="cosine"
        )
        assert result["success"] is True
        assert result["index"]["name"] == "new-index"

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_describe_index(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "name": "test-index",
                    "dimension": 1536,
                    "metric": "cosine",
                    "host": "test.svc.pinecone.io",
                    "status": {"ready": True},
                }
            ),
        )
        result = self._fn("pinecone_describe_index")(name="test-index")
        assert result["success"] is True
        assert result["index"]["name"] == "test-index"

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.delete")
    def test_delete_index(self, mock_delete):
        mock_delete.return_value = MagicMock(status_code=202)
        result = self._fn("pinecone_delete_index")(name="test-index")
        assert result["success"] is True


class TestVectorTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-key"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_vectors(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"upsertedCount": 2}),
        )
        vectors = [
            {"id": "doc1", "values": [0.1, 0.2]},
            {"id": "doc2", "values": [0.3, 0.4]},
        ]
        result = self._fn("pinecone_upsert_vectors")(
            index_host="test.svc.pinecone.io", vectors=vectors
        )
        assert result["success"] is True
        assert result["upserted_count"] == 2

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_query_vectors(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "matches": [{"id": "doc1", "score": 0.95, "metadata": {"title": "Test"}}],
                    "namespace": "",
                }
            ),
        )
        result = self._fn("pinecone_query_vectors")(
            index_host="test.svc.pinecone.io",
            vector=[0.1, 0.2, 0.3],
            top_k=5,
        )
        assert result["success"] is True
        assert result["count"] == 1

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_fetch_vectors(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "vectors": {"doc1": {"id": "doc1", "values": [0.1, 0.2], "metadata": {}}},
                    "namespace": "",
                }
            ),
        )
        result = self._fn("pinecone_fetch_vectors")(index_host="test.svc.pinecone.io", ids=["doc1"])
        assert result["success"] is True
        assert result["count"] == 1

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_delete_vectors(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        result = self._fn("pinecone_delete_vectors")(
            index_host="test.svc.pinecone.io", ids=["doc1"]
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_vectors_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timed out")
        result = self._fn("pinecone_upsert_vectors")(
            index_host="test.svc.pinecone.io", vectors=[{"id": "1", "values": [0.1]}]
        )
        assert "error" in result
        assert "timed out" in result["error"]

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_query_vectors_network_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("connection failed")
        result = self._fn("pinecone_query_vectors")(
            index_host="test.svc.pinecone.io", vector=[0.1, 0.2]
        )
        assert "error" in result
        assert "Network error" in result["error"]


class TestRecordTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-key"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_upsert_records(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        records = [{"_id": "doc1", "title": "Test Document"}]
        result = self._fn("pinecone_upsert_records")(
            index_host="test.svc.pinecone.io", records=records
        )
        assert result["success"] is True

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.post")
    def test_search_records(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "result": {
                        "hits": [{"_id": "doc1", "_score": 0.95, "fields": {"title": "Test"}}]
                    }
                }
            ),
        )
        result = self._fn("pinecone_search_records")(
            index_host="test.svc.pinecone.io",
            query={"text": "search query"},
            top_k=5,
        )
        assert result["success"] is True
        assert result["count"] == 1


class TestNamespaceTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.fns = []
        self.mcp.tool.return_value = lambda fn: self.fns.append(fn) or fn
        cred = MagicMock()
        cred.get.return_value = "test-key"
        register_tools(self.mcp, credentials=cred)

    def _fn(self, name):
        return next(f for f in self.fns if f.__name__ == name)

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.get")
    def test_list_namespaces(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "namespaces": {
                        "": {"vectorCount": 100},
                        "production": {"vectorCount": 500},
                    }
                }
            ),
        )
        result = self._fn("pinecone_list_namespaces")(index_host="test.svc.pinecone.io")
        assert result["success"] is True
        assert len(result["namespaces"]) == 2

    @patch("aden_tools.tools.pinecone_tool.pinecone_tool.httpx.delete")
    def test_delete_namespace(self, mock_delete):
        mock_delete.return_value = MagicMock(status_code=200)
        result = self._fn("pinecone_delete_namespace")(
            index_host="test.svc.pinecone.io", namespace="old-namespace"
        )
        assert result["success"] is True


class TestCredentialSpec:
    def test_pinecone_credential_spec_exists(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        assert "pinecone" in CREDENTIAL_SPECS

    def test_pinecone_spec_env_var(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["pinecone"]
        assert spec.env_var == "PINECONE_API_KEY"

    def test_pinecone_spec_tools(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["pinecone"]
        assert "pinecone_list_indexes" in spec.tools
        assert "pinecone_query_vectors" in spec.tools
        assert "pinecone_upsert_vectors" in spec.tools
        assert len(spec.tools) == 12

    def test_pinecone_spec_health_check(self):
        from aden_tools.credentials import CREDENTIAL_SPECS

        spec = CREDENTIAL_SPECS["pinecone"]
        assert spec.health_check_endpoint == "https://api.pinecone.io/indexes"
        assert spec.health_check_method == "GET"
        assert spec.credential_id == "pinecone"
        assert spec.credential_key == "api_key"
