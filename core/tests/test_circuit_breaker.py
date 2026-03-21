import threading
import time

from framework.runner.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    get_circuit_breaker,
)


def test_circuit_breaker_initial_state():
    breaker = CircuitBreaker("test_server")
    assert not breaker.is_open()
    assert breaker.get_state() == "CLOSED"
    stats = breaker.get_stats()
    assert stats["failures"] == 0
    assert stats["successes"] == 0


def test_circuit_breaker_success():
    breaker = CircuitBreaker("test_server")
    breaker.record_success()
    assert not breaker.is_open()
    assert breaker.get_state() == "CLOSED"
    stats = breaker.get_stats()
    assert stats["successes"] == 1
    assert stats["consecutive_failures"] == 0


def test_circuit_breaker_failure_threshold_opens():
    config = CircuitBreakerConfig(failure_threshold=3)
    breaker = CircuitBreaker("test_server", config)

    # 2 failures, still CLOSED
    breaker.record_failure()
    breaker.record_failure()
    assert not breaker.is_open()
    assert breaker.get_state() == "CLOSED"

    # 3rd failure opens the circuit
    breaker.record_failure()
    assert breaker.is_open()
    assert breaker.get_state() == "OPEN"

    stats = breaker.get_stats()
    assert stats["failures"] == 3
    assert stats["consecutive_failures"] == 3


def test_circuit_breaker_half_open_transition():
    # Set short recovery timeout for testing
    config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
    breaker = CircuitBreaker("test_server", config)

    # Open the circuit
    breaker.record_failure()
    assert breaker.is_open()

    # Wait for recovery timeout
    time.sleep(0.15)

    # Now it should allow a probe request (transition to HALF_OPEN)
    assert not breaker.is_open()
    assert breaker.get_state() == "HALF_OPEN"

    # Probe request succeeds, should transition back to CLOSED
    breaker.record_success()
    assert not breaker.is_open()
    assert breaker.get_state() == "CLOSED"

    # Verify stats
    stats = breaker.get_stats()
    assert stats["consecutive_failures"] == 0


def test_circuit_breaker_half_open_failure():
    config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
    breaker = CircuitBreaker("test_server", config)

    # Open the circuit
    breaker.record_failure()
    assert breaker.is_open()

    # Wait for recovery timeout
    time.sleep(0.15)

    # Transition to HALF_OPEN
    assert not breaker.is_open()
    assert breaker.get_state() == "HALF_OPEN"

    # Probe request fails, should transition back to OPEN
    breaker.record_failure()
    assert breaker.is_open()
    assert breaker.get_state() == "OPEN"


def test_circuit_breaker_thread_safety():
    breaker = CircuitBreaker("test_server")

    def worker_successes():
        for _ in range(100):
            breaker.record_success()

    def worker_failures():
        # Using a failure_threshold higher than calls to stay CLOSED for simple stats test
        for _ in range(50):
            breaker.record_failure()

    breaker.config.failure_threshold = 1000  # Prevent opening for this test

    threads = []
    for _ in range(5):
        t1 = threading.Thread(target=worker_successes)
        t2 = threading.Thread(target=worker_failures)
        threads.extend([t1, t2])
        t1.start()
        t2.start()

    for t in threads:
        t.join()

    stats = breaker.get_stats()
    assert stats["successes"] == 500
    assert stats["failures"] == 250
    assert stats["total_calls"] == 750


def test_registry_singleton():
    reg1 = CircuitBreakerRegistry.get_instance()
    reg2 = CircuitBreakerRegistry.get_instance()
    assert reg1 is reg2


def test_get_circuit_breaker_from_registry():
    breaker1 = get_circuit_breaker("server_a")
    breaker2 = get_circuit_breaker("server_a")
    breaker3 = get_circuit_breaker("server_b")

    assert breaker1 is breaker2
    assert breaker1 is not breaker3
    assert breaker1.name == "server_a"
    assert breaker3.name == "server_b"


def test_registry_reset_all():
    breaker1 = get_circuit_breaker("server_reset_1", CircuitBreakerConfig(failure_threshold=1))
    breaker2 = get_circuit_breaker("server_reset_2", CircuitBreakerConfig(failure_threshold=1))

    breaker1.record_failure()
    breaker2.record_failure()

    assert breaker1.is_open()
    assert breaker2.is_open()

    CircuitBreakerRegistry.get_instance().reset_all()

    assert not breaker1.is_open()
    assert not breaker2.is_open()
    assert breaker1.get_state() == "CLOSED"
    assert breaker2.get_state() == "CLOSED"
