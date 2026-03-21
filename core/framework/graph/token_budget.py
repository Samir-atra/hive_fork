import logging
import threading

logger = logging.getLogger("framework.graph.token_budget")


class TokenBudgetExceededError(Exception):
    """Exception raised when execution exceeds the configured token budget.

    Attributes:
        budget (int): The maximum allowed tokens.
        current (int): The total accumulated tokens that exceeded the budget.
        node_id (str | None): The ID of the node being executed when the limit was exceeded.
    """

    def __init__(self, budget: int, current: int, node_id: str | None = None):
        self.budget = budget
        self.current = current
        self.node_id = node_id
        msg = f"Token budget exceeded: consumed {current} tokens (limit: {budget})"
        if node_id:
            msg += f" during execution of node '{node_id}'"
        super().__init__(msg)


class TokenBudget:
    """Thread-safe cumulative token budget tracker.

    Args:
        limit (int | None): Maximum tokens allowed. If None, budget is unlimited.
    """

    def __init__(self, limit: int | None = None):
        self.limit = limit
        self._current_tokens = 0
        self._lock = threading.RLock()
        self._warning_logged = False

    def record(self, tokens: int, node_id: str | None = None) -> None:
        """Record token consumption and check if the budget is exceeded.

        Args:
            tokens: Number of tokens consumed in the current step.
            node_id: Optional node ID associated with the token consumption.

        Raises:
            TokenBudgetExceededError: If the accumulated tokens exceed the limit.
        """
        if tokens <= 0:
            return

        with self._lock:
            self._current_tokens += tokens

            if self.limit is None:
                return

            if self._current_tokens > self.limit:
                raise TokenBudgetExceededError(self.limit, self._current_tokens, node_id)

            # Log warning at 80% capacity
            if not self._warning_logged and self._current_tokens >= (self.limit * 0.8):
                logger.warning(
                    f"Token budget warning: {self._current_tokens}/{self.limit} "
                    f"({(self._current_tokens / self.limit) * 100:.1f}%) consumed."
                )
                self._warning_logged = True

    @property
    def current(self) -> int:
        """Get the current accumulated tokens."""
        with self._lock:
            return self._current_tokens
