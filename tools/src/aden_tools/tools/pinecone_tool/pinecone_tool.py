"""
Pinecone Tool - Vector database operations for RAG agent workflows.

Supports:
- Index management (list, create, describe, delete)
- Vector operations (upsert, query, fetch, delete)
- Record operations with integrated inference (upsert, search)
- Namespace management (list, delete)

API Reference: https://docs.pinecone.io/reference/api/introduction
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

PINECONE_API_BASE = "https://api.pinecone.io"


class _PineconeClient:
    """Internal client wrapping Pinecone REST API calls."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Pinecone API response."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Pinecone API key"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions for this operation"}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "Rate limit exceeded. Please try again later."}
        if response.status_code >= 500:
            return {"error": f"Pinecone server error: {response.status_code}"}

        if response.status_code not in (200, 201, 202):
            return {"error": f"HTTP error {response.status_code}: {response.text}"}

        try:
            return response.json()
        except Exception:
            return {"success": True, "status_code": response.status_code}

    def list_indexes(self) -> dict[str, Any]:
        """List all indexes in the project."""
        response = httpx.get(
            f"{PINECONE_API_BASE}/indexes",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_index(
        self,
        name: str,
        dimension: int,
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1",
        spec: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new index."""
        if spec:
            body = {"name": name, "dimension": dimension, "metric": metric, "spec": spec}
        else:
            body = {
                "name": name,
                "dimension": dimension,
                "metric": metric,
                "spec": {"serverless": {"cloud": cloud, "region": region}},
            }
        response = httpx.post(
            f"{PINECONE_API_BASE}/indexes",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def describe_index(self, name: str) -> dict[str, Any]:
        """Get details about an index."""
        response = httpx.get(
            f"{PINECONE_API_BASE}/indexes/{name}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_index(self, name: str) -> dict[str, Any]:
        """Delete an index."""
        response = httpx.delete(
            f"{PINECONE_API_BASE}/indexes/{name}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def upsert_vectors(
        self,
        index_host: str,
        vectors: list[dict[str, Any]],
        namespace: str = "",
    ) -> dict[str, Any]:
        """Upsert vectors into an index.

        Args:
            index_host: Index host URL (from describe_index)
            vectors: List of vectors, each with 'id', 'values', and optional 'metadata'
            namespace: Optional namespace within the index
        """
        body: dict[str, Any] = {"vectors": vectors}
        if namespace:
            body["namespace"] = namespace

        response = httpx.post(
            f"https://{index_host}/vectors/upsert",
            headers=self._headers,
            json=body,
            timeout=60.0,
        )
        return self._handle_response(response)

    def query_vectors(
        self,
        index_host: str,
        vector: list[float] | None = None,
        id: str | None = None,
        top_k: int = 10,
        namespace: str = "",
        filter: dict[str, Any] | None = None,
        include_values: bool = False,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Query an index for similar vectors.

        Args:
            index_host: The host URL of the index
            vector: Query vector (required if id not provided)
            id: ID of existing vector to use as query (required if vector not provided)
            top_k: Number of results to return
            namespace: Optional namespace within the index
            filter: Optional metadata filter
            include_values: Whether to include vector values in results
            include_metadata: Whether to include metadata in results
        """
        body: dict[str, Any] = {
            "top_k": top_k,
            "include_values": include_values,
            "include_metadata": include_metadata,
        }
        if vector is not None:
            body["vector"] = vector
        elif id is not None:
            body["id"] = id
        else:
            return {"error": "Either 'vector' or 'id' must be provided"}

        if namespace:
            body["namespace"] = namespace
        if filter:
            body["filter"] = filter

        response = httpx.post(
            f"https://{index_host}/query",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def fetch_vectors(
        self,
        index_host: str,
        ids: list[str],
        namespace: str = "",
    ) -> dict[str, Any]:
        """Fetch vectors by ID.

        Args:
            index_host: The host URL of the index
            ids: List of vector IDs to fetch
            namespace: Optional namespace within the index
        """
        params: dict[str, Any] = {"ids": ids}
        if namespace:
            params["namespace"] = namespace

        response = httpx.get(
            f"https://{index_host}/vectors/fetch",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_vectors(
        self,
        index_host: str,
        ids: list[str] | None = None,
        delete_all: bool = False,
        namespace: str = "",
        filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Delete vectors from an index.

        Args:
            index_host: The host URL of the index
            ids: List of vector IDs to delete
            delete_all: If True, delete all vectors in namespace
            namespace: Namespace within the index
            filter: Optional metadata filter for deletion
        """
        body: dict[str, Any] = {}
        if delete_all:
            body["deleteAll"] = True
        elif ids:
            body["ids"] = ids
        elif filter:
            body["filter"] = filter
        else:
            return {"error": "Must provide 'ids', 'delete_all', or 'filter'"}

        if namespace:
            body["namespace"] = namespace

        response = httpx.post(
            f"https://{index_host}/vectors/delete",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def upsert_records(
        self,
        index_host: str,
        records: list[dict[str, Any]],
        namespace: str = "",
    ) -> dict[str, Any]:
        """Upsert records using integrated inference.

        This endpoint uses Pinecone's integrated inference to automatically
        generate embeddings from text data.

        Args:
            index_host: The host URL of the index (must be an integrated inference index)
            records: List of records with '_id' and data fields matching the index model
            namespace: Optional namespace within the index
        """
        body: dict[str, Any] = {"records": records}
        if namespace:
            body["namespace"] = namespace

        response = httpx.post(
            f"https://{index_host}/records/upsert",
            headers=self._headers,
            json=body,
            timeout=60.0,
        )
        return self._handle_response(response)

    def search_records(
        self,
        index_host: str,
        query: dict[str, Any],
        namespace: str = "",
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search records using integrated inference.

        This endpoint uses Pinecone's integrated inference to automatically
        generate query embeddings from text.

        Args:
            index_host: The host URL of the index (must be an integrated inference index)
            query: Query dict with fields matching the index model's text field
            namespace: Optional namespace within the index
            top_k: Number of results to return
            filter: Optional metadata filter
        """
        body: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        if namespace:
            body["namespace"] = namespace
        if filter:
            body["filter"] = filter

        response = httpx.post(
            f"https://{index_host}/records/search",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)

    def list_namespaces(
        self,
        index_host: str,
    ) -> dict[str, Any]:
        """List all namespaces in an index."""
        response = httpx.get(
            f"https://{index_host}/namespaces",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_namespace(
        self,
        index_host: str,
        namespace: str,
    ) -> dict[str, Any]:
        """Delete a namespace and all vectors within it."""
        response = httpx.delete(
            f"https://{index_host}/namespaces/{namespace}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def describe_index_stats(
        self,
        index_host: str,
        filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get statistics about an index."""
        body: dict[str, Any] = {}
        if filter:
            body["filter"] = filter

        response = httpx.post(
            f"https://{index_host}/describe_index_stats",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Pinecone tools with the MCP server."""

    def _get_api_key() -> str | None:
        """Get Pinecone API key from credential manager or environment."""
        if credentials is not None:
            return credentials.get("pinecone")
        return os.getenv("PINECONE_API_KEY")

    def _get_client() -> _PineconeClient | dict[str, str]:
        """Get a Pinecone client, or return an error dict if no credentials."""
        api_key = _get_api_key()
        if not api_key:
            return {
                "error": "Pinecone credentials not configured",
                "help": (
                    "Set PINECONE_API_KEY environment variable or configure via credential store"
                ),
            }
        return _PineconeClient(api_key)

    @mcp.tool()
    def pinecone_list_indexes() -> dict:
        """
        List all indexes in your Pinecone project.

        Returns:
            Dict with list of indexes or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_indexes()
            if "error" in result:
                return result
            indexes = result.get("indexes", [])
            return {
                "success": True,
                "indexes": [
                    {
                        "name": idx.get("name"),
                        "dimension": idx.get("dimension"),
                        "metric": idx.get("metric"),
                        "host": idx.get("host"),
                        "spec": idx.get("spec"),
                        "status": idx.get("status", {}).get("ready", False),
                    }
                    for idx in indexes
                ],
                "count": len(indexes),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_create_index(
        name: str,
        dimension: int,
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1",
    ) -> dict:
        """
        Create a new Pinecone serverless index.

        Args:
            name: Index name (must be unique within project)
            dimension: Vector dimension (e.g., 1536 for OpenAI embeddings)
            metric: Distance metric - 'cosine', 'dotproduct', or 'euclidean'
            cloud: Cloud provider - 'aws', 'gcp', or 'azure'
            region: Region for the index (e.g., 'us-east-1', 'us-west-4')

        Returns:
            Dict with created index details or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.create_index(name, dimension, metric, cloud, region)
            if "error" in result:
                return result
            return {
                "success": True,
                "index": {
                    "name": result.get("name"),
                    "dimension": result.get("dimension"),
                    "metric": result.get("metric"),
                    "host": result.get("host"),
                    "status": result.get("status"),
                },
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_describe_index(name: str) -> dict:
        """
        Get details about a specific Pinecone index.

        Args:
            name: Index name

        Returns:
            Dict with index details including host URL needed for vector operations
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.describe_index(name)
            if "error" in result:
                return result
            return {
                "success": True,
                "index": {
                    "name": result.get("name"),
                    "dimension": result.get("dimension"),
                    "metric": result.get("metric"),
                    "host": result.get("host"),
                    "spec": result.get("spec"),
                    "status": result.get("status"),
                },
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_delete_index(name: str) -> dict:
        """
        Delete a Pinecone index.

        WARNING: This permanently deletes the index and all its data.

        Args:
            name: Index name to delete

        Returns:
            Dict with success status or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.delete_index(name)
            if "error" in result:
                return result
            return {"success": True, "message": f"Index '{name}' deleted"}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_upsert_vectors(
        index_host: str,
        vectors: list[dict],
        namespace: str = "",
    ) -> dict:
        """
        Upsert vectors into a Pinecone index.

        Args:
            index_host: Index host URL (from describe_index, e.g., 'my-index.svc.apw5.pinecone.io')
            vectors: List of vectors, each with:
                     - id: Unique identifier (string)
                     - values: Vector values (list of floats)
                     - metadata: Optional dict of key-value pairs
            namespace: Optional namespace within the index

        Returns:
            Dict with upsert count or error

        Example:
            vectors = [
                {"id": "doc1", "values": [0.1, 0.2, ...], "metadata": {"title": "Doc 1"}},
                {"id": "doc2", "values": [0.3, 0.4, ...], "metadata": {"title": "Doc 2"}}
            ]
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.upsert_vectors(index_host, vectors, namespace)
            if "error" in result:
                return result
            return {
                "success": True,
                "upserted_count": result.get("upsertedCount", len(vectors)),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_query_vectors(
        index_host: str,
        vector: list[float] | None = None,
        id: str | None = None,
        top_k: int = 10,
        namespace: str = "",
        filter: dict | None = None,
        include_values: bool = False,
        include_metadata: bool = True,
    ) -> dict:
        """
        Query a Pinecone index for similar vectors.

        Provide either 'vector' (query embedding) or 'id' (existing vector ID).

        Args:
            index_host: Index host URL
            vector: Query vector values (list of floats)
            id: ID of existing vector to use as query
            top_k: Number of results to return (default 10)
            namespace: Optional namespace to search within
            filter: Optional metadata filter (e.g., {"category": "tech"})
            include_values: Whether to include vector values in results
            include_metadata: Whether to include metadata in results

        Returns:
            Dict with matching vectors or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.query_vectors(
                index_host,
                vector=vector,
                id=id,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_values=include_values,
                include_metadata=include_metadata,
            )
            if "error" in result:
                return result
            matches = result.get("matches", [])
            return {
                "success": True,
                "matches": [
                    {
                        "id": m.get("id"),
                        "score": m.get("score"),
                        "values": m.get("values") if include_values else None,
                        "metadata": m.get("metadata") if include_metadata else None,
                    }
                    for m in matches
                ],
                "namespace": result.get("namespace", ""),
                "count": len(matches),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_fetch_vectors(
        index_host: str,
        ids: list[str],
        namespace: str = "",
    ) -> dict:
        """
        Fetch vectors by their IDs.

        Args:
            index_host: Index host URL
            ids: List of vector IDs to fetch
            namespace: Optional namespace within the index

        Returns:
            Dict with fetched vectors or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.fetch_vectors(index_host, ids, namespace)
            if "error" in result:
                return result
            vectors = result.get("vectors", {})
            return {
                "success": True,
                "vectors": {
                    vid: {
                        "id": v.get("id"),
                        "values": v.get("values"),
                        "metadata": v.get("metadata"),
                    }
                    for vid, v in vectors.items()
                },
                "namespace": result.get("namespace", ""),
                "count": len(vectors),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_delete_vectors(
        index_host: str,
        ids: list[str] | None = None,
        delete_all: bool = False,
        namespace: str = "",
        filter: dict | None = None,
    ) -> dict:
        """
        Delete vectors from a Pinecone index.

        Must provide exactly one of: ids, delete_all, or filter.

        Args:
            index_host: Index host URL
            ids: List of vector IDs to delete
            delete_all: If True, delete all vectors in the namespace
            namespace: Namespace within the index
            filter: Metadata filter for selective deletion

        Returns:
            Dict with success status or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.delete_vectors(
                index_host,
                ids=ids,
                delete_all=delete_all,
                namespace=namespace,
                filter=filter,
            )
            if "error" in result:
                return result
            return {"success": True, "message": "Vectors deleted"}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_upsert_records(
        index_host: str,
        records: list[dict],
        namespace: str = "",
    ) -> dict:
        """
        Upsert records using Pinecone's integrated inference.

        This endpoint automatically generates embeddings from text data.
        Requires an index created with an embedding model.

        Args:
            index_host: Index host URL (must be integrated inference index)
            records: List of records with '_id' and text fields matching index model
            namespace: Optional namespace within the index

        Returns:
            Dict with success status or error

        Example:
            records = [
                {"_id": "doc1", "title": "Document Title", "content": "Full text..."}
            ]
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.upsert_records(index_host, records, namespace)
            if "error" in result:
                return result
            return {"success": True, "message": f"Upserted {len(records)} records"}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_search_records(
        index_host: str,
        query: dict,
        namespace: str = "",
        top_k: int = 10,
        filter: dict | None = None,
    ) -> dict:
        """
        Search records using Pinecone's integrated inference.

        This endpoint automatically generates query embeddings from text.
        Requires an index created with an embedding model.

        Args:
            index_host: Index host URL (must be integrated inference index)
            query: Query dict with text field matching index model (e.g., {"text": "search query"})
            namespace: Optional namespace to search within
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            Dict with matching records or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.search_records(
                index_host,
                query,
                namespace=namespace,
                top_k=top_k,
                filter=filter,
            )
            if "error" in result:
                return result
            hits = result.get("result", {}).get("hits", [])
            return {
                "success": True,
                "hits": [
                    {
                        "_id": h.get("_id"),
                        "_score": h.get("_score"),
                        "fields": h.get("fields"),
                    }
                    for h in hits
                ],
                "count": len(hits),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_list_namespaces(index_host: str) -> dict:
        """
        List all namespaces in a Pinecone index.

        Args:
            index_host: Index host URL

        Returns:
            Dict with list of namespaces or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_namespaces(index_host)
            if "error" in result:
                return result
            namespaces = result.get("namespaces", {})
            return {
                "success": True,
                "namespaces": [
                    {"name": name, "vector_count": ns.get("vectorCount", 0)}
                    for name, ns in namespaces.items()
                ],
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def pinecone_delete_namespace(
        index_host: str,
        namespace: str,
    ) -> dict:
        """
        Delete a namespace and all vectors within it.

        WARNING: This permanently deletes all data in the namespace.

        Args:
            index_host: Index host URL
            namespace: Namespace name to delete

        Returns:
            Dict with success status or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.delete_namespace(index_host, namespace)
            if "error" in result:
                return result
            return {"success": True, "message": f"Namespace '{namespace}' deleted"}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
