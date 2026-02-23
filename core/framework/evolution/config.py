"""Configuration models for agent evolution.

An AgentConfiguration represents the configurable aspects of an agent:
- System prompts
- Evaluation rules
- Confidence thresholds
- Tool selection

Configurations evolve through mutations, with fitness determined by
HybridJudge evaluations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class GeneType(str, Enum):
    """Types of configuration genes."""

    SYSTEM_PROMPT = "system_prompt"
    EVALUATION_RULE = "evaluation_rule"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    TOOL_SELECTION = "tool_selection"
    MAX_ITERATIONS = "max_iterations"
    RETRY_BEHAVIOR = "retry_behavior"


@dataclass
class ConfigurationGene:
    """A single configurable aspect of an agent.

    Genes are the unit of mutation in the evolution system.
    """

    gene_type: GeneType
    name: str
    value: Any
    description: str = ""

    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[Any] | None = None

    mutation_rate: float = 0.1
    mutation_strength: float = 0.2

    def validate(self, new_value: Any) -> bool:
        """Validate a potential new value for this gene."""
        if self.allowed_values is not None:
            return new_value in self.allowed_values

        if isinstance(self.value, (int, float)):
            if self.min_value is not None and new_value < self.min_value:
                return False
            if self.max_value is not None and new_value > self.max_value:
                return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "gene_type": self.gene_type.value,
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "allowed_values": self.allowed_values,
            "mutation_rate": self.mutation_rate,
            "mutation_strength": self.mutation_strength,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigurationGene":
        return cls(
            gene_type=GeneType(data["gene_type"]),
            name=data["name"],
            value=data["value"],
            description=data.get("description", ""),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            allowed_values=data.get("allowed_values"),
            mutation_rate=data.get("mutation_rate", 0.1),
            mutation_strength=data.get("mutation_strength", 0.2),
        )


@dataclass
class AgentConfiguration:
    """Complete configuration for an agent.

    A configuration is a collection of genes that together define
    agent behavior. Configurations are evaluated for fitness and
    evolved over time.
    """

    config_id: str = field(default_factory=lambda: uuid4().hex[:12])
    agent_id: str = ""
    version: int = 1
    parent_id: str | None = None

    genes: list[ConfigurationGene] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    fitness_score: float = 0.0
    evaluation_count: int = 0

    status: str = "candidate"  # "candidate" | "approved" | "deployed" | "rejected"

    def get_gene(self, name: str) -> ConfigurationGene | None:
        """Get a gene by name."""
        for gene in self.genes:
            if gene.name == name:
                return gene
        return None

    def get_gene_value(self, name: str, default: Any = None) -> Any:
        """Get a gene's value by name."""
        gene = self.get_gene(name)
        return gene.value if gene else default

    def set_gene_value(self, name: str, value: Any) -> bool:
        """Set a gene's value. Returns True if successful."""
        gene = self.get_gene(name)
        if gene is None:
            return False
        if not gene.validate(value):
            return False
        gene.value = value
        return True

    def get_system_prompt(self) -> str:
        """Get the system prompt gene value."""
        return self.get_gene_value("system_prompt", "")

    def get_confidence_threshold(self) -> float:
        """Get the confidence threshold gene value."""
        return self.get_gene_value("confidence_threshold", 0.7)

    def get_evaluation_rules(self) -> list[dict[str, Any]]:
        """Get the evaluation rules gene value."""
        return self.get_gene_value("evaluation_rules", [])

    def clone(self, new_id: str | None = None) -> "AgentConfiguration":
        """Create a copy of this configuration."""
        return AgentConfiguration(
            config_id=new_id or uuid4().hex[:12],
            agent_id=self.agent_id,
            version=self.version + 1,
            parent_id=self.config_id,
            genes=[ConfigurationGene.from_dict(g.to_dict()) for g in self.genes],
            metadata=dict(self.metadata),
            status="candidate",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "agent_id": self.agent_id,
            "version": self.version,
            "parent_id": self.parent_id,
            "genes": [g.to_dict() for g in self.genes],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "fitness_score": self.fitness_score,
            "evaluation_count": self.evaluation_count,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfiguration":
        return cls(
            config_id=data.get("config_id", uuid4().hex[:12]),
            agent_id=data.get("agent_id", ""),
            version=data.get("version", 1),
            parent_id=data.get("parent_id"),
            genes=[ConfigurationGene.from_dict(g) for g in data.get("genes", [])],
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            fitness_score=data.get("fitness_score", 0.0),
            evaluation_count=data.get("evaluation_count", 0),
            status=data.get("status", "candidate"),
        )

    @classmethod
    def create_default(cls, agent_id: str = "") -> "AgentConfiguration":
        """Create a default configuration with standard genes."""
        return cls(
            agent_id=agent_id,
            genes=[
                ConfigurationGene(
                    gene_type=GeneType.SYSTEM_PROMPT,
                    name="system_prompt",
                    value="You are a helpful AI assistant.",
                    description="The system prompt for the agent",
                    mutation_rate=0.05,
                ),
                ConfigurationGene(
                    gene_type=GeneType.CONFIDENCE_THRESHOLD,
                    name="confidence_threshold",
                    value=0.7,
                    description="Minimum confidence for autonomous decisions",
                    min_value=0.5,
                    max_value=0.95,
                    mutation_rate=0.1,
                    mutation_strength=0.05,
                ),
                ConfigurationGene(
                    gene_type=GeneType.MAX_ITERATIONS,
                    name="max_iterations",
                    value=50,
                    description="Maximum event loop iterations",
                    min_value=10,
                    max_value=200,
                    mutation_rate=0.05,
                ),
                ConfigurationGene(
                    gene_type=GeneType.RETRY_BEHAVIOR,
                    name="max_retries",
                    value=3,
                    description="Maximum retries per node",
                    min_value=1,
                    max_value=10,
                    mutation_rate=0.05,
                ),
            ],
        )


@dataclass
class ConfigurationVariant:
    """A variant of a configuration for A/B testing.

    Variants track performance metrics during testing.
    """

    variant_id: str = field(default_factory=lambda: uuid4().hex[:8])
    config: AgentConfiguration = field(default_factory=AgentConfiguration)

    test_start: str = ""
    test_end: str = ""
    test_status: str = "pending"  # "pending" | "running" | "completed"

    runs: int = 0
    successes: int = 0
    failures: int = 0
    escalations: int = 0

    total_tokens: int = 0
    total_latency_ms: int = 0

    shadow_test_results: list[dict[str, Any]] = field(default_factory=list)
    human_feedback: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.successes / self.runs

    @property
    def escalation_rate(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.escalations / self.runs

    @property
    def avg_latency_ms(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.total_latency_ms / self.runs

    @property
    def avg_tokens(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.total_tokens / self.runs

    def record_run(
        self,
        success: bool,
        escalated: bool = False,
        tokens: int = 0,
        latency_ms: int = 0,
    ) -> None:
        """Record the result of a single run."""
        self.runs += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        if escalated:
            self.escalations += 1
        self.total_tokens += tokens
        self.total_latency_ms += latency_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "config": self.config.to_dict(),
            "test_start": self.test_start,
            "test_end": self.test_end,
            "test_status": self.test_status,
            "runs": self.runs,
            "successes": self.successes,
            "failures": self.failures,
            "escalations": self.escalations,
            "total_tokens": self.total_tokens,
            "total_latency_ms": self.total_latency_ms,
            "shadow_test_results": self.shadow_test_results,
            "human_feedback": self.human_feedback,
            "success_rate": self.success_rate,
            "escalation_rate": self.escalation_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_tokens": self.avg_tokens,
        }
