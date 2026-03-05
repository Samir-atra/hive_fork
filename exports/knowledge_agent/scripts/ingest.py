#!/usr/bin/env python3
"""Document ingestion script for Knowledge Agent.

This script processes documents from a directory, chunks them, generates embeddings,
and stores them in a vector database for retrieval.

Usage:
    python scripts/ingest.py --docs ./knowledge_base/
    python scripts/ingest.py --docs ./knowledge_base/ --rebuild
"""

import argparse
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import numpy as np


class SimpleVectorStore:
    """Simple JSON-based vector store for development and testing."""

    def __init__(self, store_path: str = "~/.hive/knowledge_agent/vector_store.json"):
        self.store_path = Path(store_path).expanduser()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load existing vector store."""
        if self.store_path.exists():
            with open(self.store_path, "r") as f:
                return json.load(f)
        return {"chunks": [], "embeddings": [], "metadata": {}}

    def _save(self):
        """Save vector store to disk."""
        with open(self.store_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """Add document chunks with their embeddings."""
        self.data["chunks"].extend(chunks)
        self.data["embeddings"].extend(embeddings)
        self._save()
        print(f"Added {len(chunks)} chunks to vector store")

    def clear(self):
        """Clear all data from the vector store."""
        self.data = {"chunks": [], "embeddings": [], "metadata": {}}
        self._save()
        print("Vector store cleared")

    def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using cosine similarity."""
        if not self.data["embeddings"]:
            return []

        query_vec = np.array(query_embedding)
        embeddings = np.array(self.data["embeddings"])

        # Compute cosine similarity
        similarities = np.dot(embeddings, query_vec) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec)
        )

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.data["chunks"][idx].copy()
            chunk["relevance_score"] = float(similarities[idx])
            results.append(chunk)

        return results


class DocumentChunker:
    """Split documents into overlapping chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, source: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i : i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            # Generate unique ID for chunk
            chunk_id = hashlib.md5(f"{source}:{i}".encode()).hexdigest()[:12]

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "content": chunk_text,
                    "source": source,
                    "start_index": i,
                    "end_index": min(i + self.chunk_size, len(words)),
                }
            )

        return chunks


def generate_simple_embedding(text: str) -> List[float]:
    """Generate a simple embedding for demonstration.

    In production, you would use:
    - OpenAI embeddings (text-embedding-3-small)
    - Anthropic embeddings
    - Local embeddings (sentence-transformers)

    For this demo, we create a simple hash-based embedding.
    """
    # Create a deterministic pseudo-embedding based on text hash
    # This is NOT suitable for production - use real embeddings!
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Convert hash to numeric values and normalize
    embedding = []
    for i in range(0, 64, 4):  # Create 16-dimensional embedding
        value = int(text_hash[i : i + 4], 16) / 65535.0
        embedding.append(value)

    return embedding


def load_documents(docs_dir: Path) -> List[Dict[str, str]]:
    """Load all markdown and text documents from directory."""
    documents = []

    for ext in ["*.md", "*.txt"]:
        for file_path in docs_dir.glob(ext):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append(
                    {
                        "path": str(file_path),
                        "filename": file_path.name,
                        "content": content,
                    }
                )

    return documents


def ingest_documents(docs_dir: str, rebuild: bool = False):
    """Main ingestion pipeline."""
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        print(f"Error: Directory '{docs_dir}' does not exist")
        return

    print(f"Ingesting documents from: {docs_dir}")

    # Initialize components
    store = SimpleVectorStore()
    chunker = DocumentChunker()

    # Clear existing data if rebuild requested
    if rebuild:
        store.clear()

    # Load documents
    documents = load_documents(docs_path)
    print(f"Found {len(documents)} documents")

    if not documents:
        print("No documents to process")
        return

    # Process each document
    all_chunks = []
    all_embeddings = []

    for doc in documents:
        print(f"Processing: {doc['filename']}")

        # Chunk the document
        chunks = chunker.chunk_text(doc["content"], doc["filename"])
        print(f"  Created {len(chunks)} chunks")

        # Generate embeddings for each chunk
        embeddings = []
        for chunk in chunks:
            embedding = generate_simple_embedding(chunk["content"])
            embeddings.append(embedding)

        all_chunks.extend(chunks)
        all_embeddings.extend(embeddings)

    # Add to vector store
    store.add_chunks(all_chunks, all_embeddings)

    print(f"\nIngestion complete!")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Vector store location: {store.store_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into the Knowledge Agent vector store"
    )
    parser.add_argument(
        "--docs",
        type=str,
        required=True,
        help="Path to directory containing documents to ingest",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear existing vector store before ingesting",
    )

    args = parser.parse_args()
    ingest_documents(args.docs, args.rebuild)


if __name__ == "__main__":
    main()
