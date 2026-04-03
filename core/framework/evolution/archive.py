import json
import sqlite3
from datetime import datetime

from pydantic import BaseModel


class TaskDef(BaseModel):
    id: str
    description: str

class ModelConfig(BaseModel):
    reflection: str
    mutation: str
    eval: str
    triage: str

class BudgetConfig(BaseModel):
    max_iterations: int
    max_cost: float
    convergence_threshold: int

class SelectionConfig(BaseModel):
    k: int
    m: int
    novelty_weight: float

class EvolutionCampaign(BaseModel):
    name: str
    agent_path: str
    task_suite: list[TaskDef]
    models: ModelConfig
    budget: BudgetConfig
    selection: SelectionConfig

class EvolvedAgent(BaseModel):
    id: int | None = None
    iteration: int
    parent_ids: list[int]
    config_hash: str
    agent_config: dict
    connection_code: dict
    performance_score: float
    performance_vector: list[int]
    trace_summary: dict
    evolution_directives: str
    created_at: datetime

class EvolutionArchive:
    """A SQLite-backed archive for storing evolved agent configurations and their performance."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._memory_conn = None
        self._init_db()

    def _get_conn(self):
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path)
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        iteration INTEGER NOT NULL,
                        parent_ids TEXT NOT NULL,
                        config_hash TEXT NOT NULL,
                        agent_config TEXT NOT NULL,
                        connection_code TEXT NOT NULL,
                        performance_score REAL NOT NULL,
                        performance_vector TEXT NOT NULL,
                        trace_summary TEXT NOT NULL,
                        evolution_directives TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def add_agent(self, agent: EvolvedAgent) -> int:
        conn = self._get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO agents (
                        iteration, parent_ids, config_hash, agent_config,
                        connection_code, performance_score, performance_vector,
                        trace_summary, evolution_directives, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent.iteration,
                        json.dumps(agent.parent_ids),
                        agent.config_hash,
                        json.dumps(agent.agent_config),
                        json.dumps(agent.connection_code),
                        agent.performance_score,
                        json.dumps(agent.performance_vector),
                        json.dumps(agent.trace_summary),
                        agent.evolution_directives,
                        agent.created_at.isoformat(),
                    ),
                )
                return cursor.lastrowid
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def get_agent(self, agent_id: int) -> EvolvedAgent | None:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM agents WHERE id = ?", (agent_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_agent(row)
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def list_agents(self, iteration: int | None = None) -> list[EvolvedAgent]:
        conn = self._get_conn()
        try:
            if iteration is not None:
                cursor = conn.execute("SELECT * FROM agents WHERE iteration = ?", (iteration,))
            else:
                cursor = conn.execute("SELECT * FROM agents")
            return [self._row_to_agent(row) for row in cursor.fetchall()]
        finally:
            if self.db_path != ":memory:":
                conn.close()

    def _row_to_agent(self, row: tuple) -> EvolvedAgent:
        return EvolvedAgent(
            id=row[0],
            iteration=row[1],
            parent_ids=json.loads(row[2]),
            config_hash=row[3],
            agent_config=json.loads(row[4]),
            connection_code=json.loads(row[5]),
            performance_score=row[6],
            performance_vector=json.loads(row[7]),
            trace_summary=json.loads(row[8]),
            evolution_directives=row[9],
            created_at=datetime.fromisoformat(row[10]),
        )
