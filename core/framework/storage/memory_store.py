import json
import logging
import math
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from framework.storage.backend import migrate_agent_memories_table

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm1 = math.sqrt(sum(x * x for x in v1))
    norm2 = math.sqrt(sum(y * y for y in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


class SQLiteMemoryStore:
    """
    Persistent memory store for agent learnings.
    Stores extracted learnings and their embeddings in an SQLite database.
    Provides local vector search via cosine similarity.
    """

    def __init__(self, base_path: str | Path):
        """
        Initialize the memory store.

        Args:
            base_path: Base directory for the agent (e.g., ~/.hive/agents/{agent_name})
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_path / "agent_memories.db"

        # Ensure the table exists
        migrate_agent_memories_table(self.db_path)

    def store_learning(self, agent_id: str, learning: str, embedding: list[float]) -> str:
        """
        Store a new learning and its embedding.

        Args:
            agent_id: Identifier for the agent.
            learning: The extracted insight.
            embedding: The vector embedding.

        Returns:
            The memory ID.
        """
        memory_id = str(uuid.uuid4())
        con = sqlite3.connect(str(self.db_path))
        try:
            con.execute(
                "INSERT INTO agent_memories (id, agent_id, learning, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    memory_id,
                    agent_id,
                    learning,
                    json.dumps(embedding),
                    datetime.now().isoformat()
                )
            )
            con.commit()
            logger.debug(f"Stored learning {memory_id} for agent {agent_id}")
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store learning: {e}")
            raise
        finally:
            con.close()

    def search_learnings(self, agent_id: str, query_embedding: list[float], limit: int = 3) -> list[str]:
        """
        Search for the most relevant learnings.

        Args:
            agent_id: Identifier for the agent.
            query_embedding: The vector embedding of the query.
            limit: Maximum number of results to return.

        Returns:
            List of learning strings.
        """
        con = sqlite3.connect(str(self.db_path))
        try:
            cur = con.cursor()
            cur.execute("SELECT learning, embedding FROM agent_memories WHERE agent_id = ?", (agent_id,))
            rows = cur.fetchall()

            if not rows:
                return []

            results = []
            for learning, embedding_str in rows:
                try:
                    embedding = json.loads(embedding_str)
                    score = cosine_similarity(query_embedding, embedding)
                    results.append((score, learning))
                except Exception as e:
                    logger.warning(f"Failed to process embedding for learning: {e}")

            # Sort by score descending
            results.sort(key=lambda x: x[0], reverse=True)
            return [learning for score, learning in results[:limit]]
        except Exception as e:
            logger.error(f"Failed to search learnings: {e}")
            return []
        finally:
            con.close()
