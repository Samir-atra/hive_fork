from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenLedger:
    """Records granular token usage and calculates cost weights for compaction.

    This ledger aligns with roadmap goals to integrate fine-grained signals
    (reasoning, caching) into the pruning strategy, protecting critical context
    frames while dropping bloated low-value text.
    """

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_reasoning_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_cost: float = 0.0

    node_costs: dict[str, float] = field(default_factory=dict)
    tool_call_costs: dict[str, float] = field(default_factory=dict)
    message_costs: dict[int, float] = field(default_factory=dict)

    def record_turn(
        self,
        node_id: str,
        message_seq: int,
        prompt_tokens: int,
        completion_tokens: int,
        reasoning_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float:
        """Record usage from an LLM call and return a computed token weight."""
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_reasoning_tokens += reasoning_tokens
        self.total_cache_read_tokens += cache_read_tokens
        self.total_cache_write_tokens += cache_write_tokens

        # Simple heuristic weight based on tokens (could be tied to actual pricing models later)
        # We penalize heavy completions and reward cached reads
        weight = completion_tokens + (prompt_tokens * 0.5) + (reasoning_tokens * 1.5)
        cost = max(weight, 1.0)
        self.total_cost += cost

        self.node_costs[node_id] = self.node_costs.get(node_id, 0.0) + cost
        self.message_costs[message_seq] = cost

        return cost

    def record_tool_call(self, tool_use_id: str, tokens: int) -> float:
        """Record usage from a tool call."""
        cost = tokens * 0.5
        self.total_cost += cost
        self.tool_call_costs[tool_use_id] = cost
        return cost

    def get_weights(self) -> dict[str, Any]:
        """Return the current metrics summary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_reasoning_tokens": self.total_reasoning_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_cost": self.total_cost,
        }
