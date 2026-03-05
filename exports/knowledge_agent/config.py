"""Configuration for Knowledge Agent."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4096

    # Vector store settings
    embedding_model: str = "text-embedding-3-small"
    vector_store_path: str = "~/.hive/knowledge_agent/vector_store.json"
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval settings
    top_k_results: int = 5
    min_relevance_score: float = 0.7

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")


@dataclass
class Metadata:
    name: str = "knowledge-agent"
    version: str = "1.0.0"
    description: str = (
        "A knowledge-based agent using RAG for intelligent question answering"
    )
    author: str = "Hive Team"


default_config = Config(
    model=os.getenv("KNOWLEDGE_AGENT_MODEL", "claude-3-5-sonnet-20241022"),
    api_key=os.getenv("KNOWLEDGE_AGENT_API_KEY"),
    api_base=os.getenv("KNOWLEDGE_AGENT_API_BASE"),
)

metadata = Metadata()
