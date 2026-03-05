"""Custom tools for Knowledge Agent."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import numpy as np


class KnowledgeBaseTool:
    """Tool for querying the knowledge base."""

    def __init__(self, store_path: str = "~/.hive/knowledge_agent/vector_store.json"):
        self.store_path = Path(store_path).expanduser()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load vector store."""
        if self.store_path.exists():
            with open(self.store_path, "r") as f:
                return json.load(f)
        return {"chunks": [], "embeddings": [], "metadata": {}}

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate simple embedding for query."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(0, 64, 4):
            value = int(text_hash[i : i + 4], 16) / 65535.0
            embedding.append(value)
        return embedding

    def query(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Query the knowledge base for relevant documents."""
        if not self.data["embeddings"]:
            return {
                "success": False,
                "error": "Knowledge base is empty. Please run the ingestion script first.",
                "results": [],
            }

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        query_vec = np.array(query_embedding)
        embeddings = np.array(self.data["embeddings"])

        # Compute cosine similarity
        similarities = np.dot(embeddings, query_vec) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec)
        )

        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.data["chunks"][idx].copy()
            chunk["relevance_score"] = float(similarities[idx])
            results.append(chunk)

        return {
            "success": True,
            "query": query,
            "num_results": len(results),
            "results": results,
        }


# Tool function for the framework
def query_knowledge_base(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Query the knowledge base for relevant documents using semantic search.

    Args:
        query: The search query
        top_k: Number of results to return (default: 5)

    Returns:
        Dictionary with search results including content and relevance scores
    """
    tool = KnowledgeBaseTool()
    return tool.query(query, top_k)
