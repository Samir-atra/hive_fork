import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Exception raised when a circuit breaker is open and a call is attempted."""

    pass


class CircuitBreaker:
    """
    A circuit breaker for remote calls (LLM, MCP, etc.) to prevent hammering
    failing dependencies.

    States:
        - CLOSED: Normal operation. Calls pass through. Records failures.
        - OPEN: Failing state. Calls are rejected immediately with CircuitOpenError.
        - HALF-OPEN: Testing state. Allows a single call to pass through to test recovery.
    """

    def __init__(
        self,
        name: str,
        enabled: bool = False,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
    ):
        """
        Initialize a circuit breaker.

        Args:
            name: Name of the circuit (for logging).
            enabled: Whether the circuit breaker is active.
            failure_threshold: Number of consecutive failures before opening.
            recovery_timeout_seconds: Time to wait in OPEN state before trying HALF-OPEN.
        """
        self.name = name
        self.enabled = enabled
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds

        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time: float | None = None

    def _on_success(self) -> None:
        """Called when a request succeeds."""
        if not self.enabled:
            return

        if self.state == "HALF-OPEN":
            logger.info("CircuitBreaker '%s' recovered. State changed to CLOSED.", self.name)
            self.state = "CLOSED"

        self.failure_count = 0

    def _on_failure(self, error: Exception) -> None:
        """Called when a request fails."""
        if not self.enabled:
            return

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "HALF-OPEN":
            # Failed the probe, go back to OPEN immediately
            logger.warning(
                "CircuitBreaker '%s' probe failed: %s. State changed back to OPEN.",
                self.name,
                error,
            )
            self.state = "OPEN"
        elif self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            # Reached threshold, open the circuit
            logger.error(
                "CircuitBreaker '%s' exceeded failure threshold (%d). State changed to OPEN.",
                self.name,
                self.failure_threshold,
            )
            self.state = "OPEN"

    def _check_state(self) -> None:
        """
        Check if the circuit is open and whether it's time to transition to HALF-OPEN.
        Raises CircuitOpenError if the circuit is OPEN.
        """
        if not self.enabled:
            return

        if self.state == "OPEN":
            assert self.last_failure_time is not None
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout_seconds:
                # Time to test the circuit
                logger.info(
                    "CircuitBreaker '%s' recovery timeout elapsed. State changed to HALF-OPEN.",
                    self.name,
                )
                self.state = "HALF-OPEN"
            else:
                remaining = self.recovery_timeout_seconds - elapsed
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN. Try again in {remaining:.1f}s."
                )

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a synchronous function through the circuit breaker.
        """
        self._check_state()
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception as e:
            self._on_failure(e)
            raise

    async def acall(
        self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute an asynchronous function through the circuit breaker.
        """
        self._check_state()
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except CircuitOpenError:
            raise
        except Exception as e:
            self._on_failure(e)
            raise

    def check_state(self) -> None:
        """Expose _check_state publicly for manual checks before yielding generators."""
        self._check_state()

    def record_success(self) -> None:
        """Expose _on_success publicly."""
        self._on_success()

    def record_failure(self, error: Exception) -> None:
        """Expose _on_failure publicly."""
        self._on_failure(error)
