import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = auto()  # Normal operation, requests flow through
    OPEN = auto()  # Degraded server, requests fail immediately
    HALF_OPEN = auto()  # Recovery probing


@dataclass
class CircuitStats:
    """Statistics for the circuit breaker."""

    failures: int = 0
    successes: int = 0
    consecutive_failures: int = 0
    total_calls: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for the circuit breaker.

    Attributes:
        failure_threshold: Number of consecutive failures before the circuit opens.
        recovery_timeout: Time in seconds to wait before transitioning to HALF_OPEN.
        success_threshold: Number of consecutive successes required to close the circuit again.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    success_threshold: int = 1


class CircuitOpenError(Exception):
    """Exception raised when the circuit breaker is open and requests are failing fast."""

    pass


class CircuitBreaker:
    """
    Circuit breaker for MCP tool calls to handle degraded servers.
    Provides fail-fast behavior instead of waiting for timeouts on every call.
    Thread-safe implementation.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        """
        Initialize the circuit breaker.

        Args:
            name: The name of the server or resource being protected.
            config: Configuration for the circuit breaker. Uses defaults if None.
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._lock = threading.RLock()

    def is_open(self) -> bool:
        """
        Check if the circuit is open. If HALF_OPEN and enough time has passed,
        allow a probing request.

        Returns:
            True if the circuit is OPEN (or HALF_OPEN but not ready to probe),
            False otherwise.
        """
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return False

            if self.state == CircuitState.OPEN:
                # Check if we should transition to HALF_OPEN
                if self.stats.last_failure_time is not None:
                    time_since_failure = time.time() - self.stats.last_failure_time
                    if time_since_failure >= self.config.recovery_timeout:
                        logger.info(
                            f"CircuitBreaker[{self.name}]: transition OPEN -> HALF_OPEN "
                            f"(recovery timeout {self.config.recovery_timeout}s elapsed)"
                        )
                        self.state = CircuitState.HALF_OPEN
                        # Reset consecutive successes/failures for the HALF_OPEN state
                        self.stats.consecutive_failures = 0
                        return False  # Allow probing request

                return True  # Still OPEN

            if self.state == CircuitState.HALF_OPEN:
                # Allow probing requests to go through. Since threads might run concurrently,
                # multiple probes could occur before the state transitions back to CLOSED or OPEN.
                # For simplicity, we allow all requests through in HALF_OPEN, relying on the
                # immediate next completed request to decide the final state transition.
                return False

            return False

    def record_success(self) -> None:
        """Record a successful request and update state if necessary."""
        with self._lock:
            self.stats.total_calls += 1
            self.stats.successes += 1
            self.stats.consecutive_failures = 0
            self.stats.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.info(
                    f"CircuitBreaker[{self.name}]: transition HALF_OPEN -> CLOSED (probe succeeded)"
                )
                self.state = CircuitState.CLOSED
                self.stats.consecutive_failures = 0

    def record_failure(self, exception: Exception | None = None) -> None:
        """
        Record a failed request and update state if necessary.

        Args:
            exception: The exception that caused the failure. Can be used for filtering
                non-failure exceptions (e.g., validation errors) in the future.
        """
        with self._lock:
            self.stats.total_calls += 1
            self.stats.failures += 1
            self.stats.consecutive_failures += 1
            self.stats.last_failure_time = time.time()

            if self.state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.config.failure_threshold:
                    logger.warning(
                        f"CircuitBreaker[{self.name}]: transition CLOSED -> OPEN "
                        f"({self.stats.consecutive_failures} consecutive failures)"
                    )
                    self.state = CircuitState.OPEN

            elif self.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"CircuitBreaker[{self.name}]: transition HALF_OPEN -> OPEN (probe failed)"
                )
                self.state = CircuitState.OPEN

    def get_state(self) -> str:
        """Get the current state as a string."""
        with self._lock:
            return self.state.name

    def get_stats(self) -> dict:
        """Get the current statistics."""
        with self._lock:
            return {
                "state": self.state.name,
                "failures": self.stats.failures,
                "successes": self.stats.successes,
                "consecutive_failures": self.stats.consecutive_failures,
                "total_calls": self.stats.total_calls,
                "last_failure_time": self.stats.last_failure_time,
                "last_success_time": self.stats.last_success_time,
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
            }

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"CircuitBreaker[{self.name}]: manual reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.stats = CircuitStats()


class CircuitBreakerRegistry:
    """Global singleton registry for circuit breakers per server."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._registry_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_circuit_breaker(
        self, server_name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a specific server.

        Args:
            server_name: The name of the server.
            config: Configuration for the circuit breaker.

        Returns:
            The circuit breaker instance for the server.
        """
        with self._registry_lock:
            if server_name not in self._breakers:
                self._breakers[server_name] = CircuitBreaker(server_name, config)
            return self._breakers[server_name]

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._registry_lock:
            for breaker in self._breakers.values():
                breaker.reset()


def get_circuit_breaker(
    server_name: str, config: CircuitBreakerConfig | None = None
) -> CircuitBreaker:
    """
    Convenience function to get a circuit breaker from the registry.

    Args:
        server_name: The name of the server.
        config: Configuration for the circuit breaker.

    Returns:
        The circuit breaker instance for the server.
    """
    return CircuitBreakerRegistry.get_instance().get_circuit_breaker(server_name, config)
