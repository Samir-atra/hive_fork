import time
from unittest.mock import patch

import pytest

from framework.utils.circuit_breaker import CircuitBreaker, CircuitOpenError


def test_circuit_breaker_disabled():
    cb = CircuitBreaker("test", enabled=False, failure_threshold=2, recovery_timeout_seconds=0.1)

    def fail():
        raise RuntimeError("failed")

    for _ in range(5):
        with pytest.raises(RuntimeError):
            cb.call(fail)

    assert cb.state == "CLOSED"


def test_circuit_breaker_threshold():
    cb = CircuitBreaker("test", enabled=True, failure_threshold=2, recovery_timeout_seconds=0.1)

    def fail():
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        cb.call(fail)
    assert cb.state == "CLOSED"

    with pytest.raises(RuntimeError):
        cb.call(fail)
    assert cb.state == "OPEN"

    with pytest.raises(CircuitOpenError):
        cb.call(fail)


def test_circuit_breaker_recovery():
    cb = CircuitBreaker("test", enabled=True, failure_threshold=2, recovery_timeout_seconds=0.1)

    def fail():
        raise RuntimeError("failed")

    def succ():
        return "ok"

    with pytest.raises(RuntimeError):
        cb.call(fail)
    with pytest.raises(RuntimeError):
        cb.call(fail)

    assert cb.state == "OPEN"

    with patch("time.time", return_value=time.time() + 0.2):
        assert cb.call(succ) == "ok"
        assert cb.state == "CLOSED"


def test_circuit_breaker_half_open_failure():
    cb = CircuitBreaker("test", enabled=True, failure_threshold=2, recovery_timeout_seconds=0.1)

    def fail():
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError):
        cb.call(fail)
    with pytest.raises(RuntimeError):
        cb.call(fail)

    assert cb.state == "OPEN"

    with patch("time.time", return_value=time.time() + 0.2):
        with pytest.raises(RuntimeError):
            cb.call(fail)
        assert cb.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_breaker_acall():
    cb = CircuitBreaker("test", enabled=True, failure_threshold=2, recovery_timeout_seconds=0.1)

    async def fail():
        raise RuntimeError("failed")

    async def succ():
        return "ok"

    with pytest.raises(RuntimeError):
        await cb.acall(fail)
    with pytest.raises(RuntimeError):
        await cb.acall(fail)

    assert cb.state == "OPEN"

    with pytest.raises(CircuitOpenError):
        await cb.acall(succ)

    with patch("time.time", return_value=time.time() + 0.2):
        assert await cb.acall(succ) == "ok"
        assert cb.state == "CLOSED"
