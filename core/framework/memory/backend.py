"""Vector Backend Protocol and Implementations.

Provides a pluggable backend interface for vector storage:
- VectorBackend: Protocol for all backends
- ChromaDBBackend: Default local development backend
- InMemoryBackend: Simple in-memory backend for testing
- FAISSBackend: Alternative for larger-scale deployments
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VectorBackend(Protocol):
    """Protocol for vector storage backends.

    All backends must implement these methods for unified access.
    """

    async def initialize(self) -> None:
        """Initialize the backend (create collections, load index, etc.)."""
        ...

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        """Insert or update vectors."""
        ...

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any], str]]:
        """Query for similar vectors.

        Returns:
            List of (id, distance, metadata, document) tuples.
        """
        ...

    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

    async def get(
        self,
        ids: list[str],
    ) -> list[tuple[str, list[float], dict[str, Any], str]]:
        """Get vectors by ID.

        Returns:
            List of (id, embedding, metadata, document) tuples.
        """
        ...

    async def count(self) -> int:
        """Get the total number of vectors."""
        ...

    async def clear(self) -> None:
        """Clear all vectors."""
        ...


class InMemoryBackend:
    """Simple in-memory vector backend for testing.

    Uses cosine similarity for search. Not persistent.
    """

    def __init__(self, embedding_dim: int = 1536) -> None:
        self._embedding_dim = embedding_dim
        self._vectors: dict[str, tuple[list[float], dict[str, Any], str]] = {}

    async def initialize(self) -> None:
        pass

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        for id_, emb, meta, doc in zip(ids, embeddings, metadatas, documents):
            self._vectors[id_] = (emb, meta, doc)

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any], str]]:
        results = []

        for id_, (emb, meta, doc) in self._vectors.items():
            if where:
                if not all(meta.get(k) == v for k, v in where.items()):
                    continue

            similarity = self._cosine_similarity(query_embedding, emb)
            results.append((id_, similarity, meta, doc))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:n_results]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self._vectors.pop(id_, None)

    async def get(
        self,
        ids: list[str],
    ) -> list[tuple[str, list[float], dict[str, Any], str]]:
        results = []
        for id_ in ids:
            if id_ in self._vectors:
                emb, meta, doc = self._vectors[id_]
                results.append((id_, emb, meta, doc))
        return results

    async def count(self) -> int:
        return len(self._vectors)

    async def clear(self) -> None:
        self._vectors.clear()

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)


class ChromaDBBackend:
    """ChromaDB backend for local development.

    ChromaDB is the default backend for local development.
    It persists data to disk and provides efficient vector search.

    Requires: pip install chromadb
    """

    def __init__(
        self,
        persist_directory: Path | str,
        collection_name: str = "episodes",
        embedding_function: Any = None,
    ) -> None:
        self._persist_directory = Path(persist_directory)
        self._collection_name = collection_name
        self._embedding_function = embedding_function
        self._client: Any = None
        self._collection: Any = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb

            self._persist_directory.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(path=str(self._persist_directory))

            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"},
            )

            logger.info(
                f"ChromaDB initialized: {self._collection_name} ({await self.count()} vectors)"
            )

        except ImportError:
            logger.warning(
                "chromadb not installed, falling back to InMemoryBackend. "
                "Install with: pip install chromadb"
            )
            raise RuntimeError("ChromaDB not installed. Install with: pip install chromadb")

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        if self._collection is None:
            await self.initialize()

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any], str]]:
        if self._collection is None:
            await self.initialize()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["distances", "metadatas", "documents"],
        )

        tuples = []
        if results and results.get("ids"):
            ids = results["ids"][0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            documents = results.get("documents", [[]])[0]

            for i, id_ in enumerate(ids):
                distance = distances[i] if i < len(distances) else 0.0
                meta = metadatas[i] if i < len(metadatas) else {}
                doc = documents[i] if i < len(documents) else ""
                similarity = 1.0 - distance
                tuples.append((id_, similarity, meta, doc))

        return tuples

    async def delete(self, ids: list[str]) -> None:
        if self._collection is None:
            await self.initialize()

        self._collection.delete(ids=ids)

    async def get(
        self,
        ids: list[str],
    ) -> list[tuple[str, list[float], dict[str, Any], str]]:
        if self._collection is None:
            await self.initialize()

        results = self._collection.get(
            ids=ids,
            include=["embeddings", "metadatas", "documents"],
        )

        tuples = []
        if results and results.get("ids"):
            ids = results["ids"]
            embeddings = results.get("embeddings", [])
            metadatas = results.get("metadatas", [])
            documents = results.get("documents", [])

            for i, id_ in enumerate(ids):
                emb = embeddings[i] if i < len(embeddings) else []
                meta = metadatas[i] if i < len(metadatas) else {}
                doc = documents[i] if i < len(documents) else ""
                tuples.append((id_, emb, meta, doc))

        return tuples

    async def count(self) -> int:
        if self._collection is None:
            return 0
        return self._collection.count()

    async def clear(self) -> None:
        if self._client is not None:
            try:
                self._client.delete_collection(self._collection_name)
            except Exception:
                pass
            self._collection = None
            await self.initialize()


class FAISSBackend:
    """FAISS backend for larger-scale deployments.

    FAISS provides efficient similarity search for large vector collections.
    Requires: pip install faiss-cpu (or faiss-gpu for GPU support)
    """

    def __init__(
        self,
        index_path: Path | str,
        embedding_dim: int = 1536,
    ) -> None:
        self._index_path = Path(index_path)
        self._embedding_dim = embedding_dim
        self._index: Any = None
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_id: dict[int, str] = {}
        self._metadatas: dict[str, dict[str, Any]] = {}
        self._documents: dict[str, str] = {}
        self._next_idx: int = 0

    async def initialize(self) -> None:
        """Initialize or load FAISS index."""
        try:
            import faiss

            self._index_path.mkdir(parents=True, exist_ok=True)
            index_file = self._index_path / "index.faiss"
            meta_file = self._index_path / "metadata.json"

            if index_file.exists():
                self._index = faiss.read_index(str(index_file))

                import json

                if meta_file.exists():
                    meta = json.loads(meta_file.read_text())
                    self._id_to_idx = meta.get("id_to_idx", {})
                    self._idx_to_id = {int(k): v for k, v in meta.get("idx_to_id", {}).items()}
                    self._metadatas = meta.get("metadatas", {})
                    self._documents = meta.get("documents", {})
                    self._next_idx = meta.get("next_idx", 0)
            else:
                self._index = faiss.IndexFlatIP(self._embedding_dim)

        except ImportError:
            raise RuntimeError("FAISS not installed. Install with: pip install faiss-cpu")

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        import json

        meta_file = self._index_path / "metadata.json"
        meta = {
            "id_to_idx": self._id_to_idx,
            "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
            "metadatas": self._metadatas,
            "documents": self._documents,
            "next_idx": self._next_idx,
        }
        meta_file.write_text(json.dumps(meta))

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        documents: list[str],
    ) -> None:
        import numpy as np

        for id_, emb, meta, doc in zip(ids, embeddings, metadatas, documents):
            if id_ in self._id_to_idx:
                idx = self._id_to_idx[id_]
                self._index.reconstruct(idx, np.array(emb, dtype=np.float32))
            else:
                idx = self._next_idx
                self._next_idx += 1
                self._id_to_idx[id_] = idx
                self._idx_to_id[idx] = id_

                self._index.add(np.array([emb], dtype=np.float32))

            self._metadatas[id_] = meta
            self._documents[id_] = doc

        self._save_metadata()

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[tuple[str, float, dict[str, Any], str]]:
        import numpy as np

        query = np.array([query_embedding], dtype=np.float32)
        distances, indices = self._index.search(query, n_results * 2)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue

            id_ = self._idx_to_id.get(int(idx))
            if id_ is None:
                continue

            meta = self._metadatas.get(id_, {})
            if where:
                if not all(meta.get(k) == v for k, v in where.items()):
                    continue

            score = float(distances[0][i])
            doc = self._documents.get(id_, "")
            results.append((id_, score, meta, doc))

            if len(results) >= n_results:
                break

        return results

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            if id_ in self._id_to_idx:
                del self._id_to_idx[id_]
                self._metadatas.pop(id_, None)
                self._documents.pop(id_, None)

        self._save_metadata()

    async def get(
        self,
        ids: list[str],
    ) -> list[tuple[str, list[float], dict[str, Any], str]]:
        import numpy as np

        results = []
        for id_ in ids:
            if id_ in self._id_to_idx:
                idx = self._id_to_idx[id_]
                emb = self._index.reconstruct(int(idx))
                meta = self._metadatas.get(id_, {})
                doc = self._documents.get(id_, "")
                results.append((id_, emb.tolist(), meta, doc))

        return results

    async def count(self) -> int:
        return self._index.ntotal if self._index else 0

    async def clear(self) -> None:
        import faiss

        self._index = faiss.IndexFlatIP(self._embedding_dim)
        self._id_to_idx.clear()
        self._idx_to_id.clear()
        self._metadatas.clear()
        self._documents.clear()
        self._next_idx = 0
        self._save_metadata()
