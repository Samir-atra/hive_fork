import time


class CircuitBreakerOpenError(Exception):
    """Raised when an operation is rejected because the circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    A simple stream circuit breaker that opens after a specified number of consecutive failures.
    When open, it immediately rejects operations for a specified reset timeout, then attempts recovery.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.consecutive_failures = 0
        self.last_failure_time = 0.0

    @property
    def is_open(self) -> bool:
        """Check if the circuit is currently open and should reject requests."""
        if self.consecutive_failures >= self.failure_threshold:
            time_since_failure = time.monotonic() - self.last_failure_time
            if time_since_failure < self.reset_timeout:
                return True
            # Timeout passed, transition to half-open implicitly.
            # Next request will either reset or trip the breaker again.
        return False

    def record_success(self) -> None:
        """Record a successful operation and reset the failure count."""
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a failed operation, potentially opening the circuit."""
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
