"""Fixtures for the CI-friendly agent test harness."""

import pytest

from framework.graph.executor import GraphExecutor
from framework.llm.mock import MockLLMProvider
from framework.runtime.core import Runtime


@pytest.fixture
def mock_llm_provider():
    """Deterministic mock LLM provider.

    Returns a MockLLMProvider that generates structurally valid responses
    without requiring API keys or network calls.
    """
    return MockLLMProvider()


@pytest.fixture
def agent_builder(tmp_path):
    """A helper to construct GraphExecutor instances for sample graphs.

    Returns a factory function that creates a GraphExecutor with a real Runtime
    and the provided nodes, edges, and other configurations.
    """

    def _builder(
        llm,
        *,
        tools=None,
        tool_executor=None,
        enable_parallel=True,
        parallel_config=None,
        loop_config=None,
    ) -> GraphExecutor:
        # Create a runtime with a temporary storage path
        runtime = Runtime(storage_path=tmp_path / "runtime")

        return GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools or [],
            tool_executor=tool_executor,
            enable_parallel_execution=enable_parallel,
            parallel_config=parallel_config,
            loop_config=loop_config or {"max_iterations": 10},
            storage_path=tmp_path / "runtime",
        )

    return _builder


@pytest.fixture
def mock_mcp_server():
    """Namespace-isolated FastMCP mock server fixture.

    Creates a mock FastMCP server instance so that parallel test executions
    do not cause race conditions. It registers a few mock tools that can be
    used by the mock agent graphs.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        # Provide a fallback if mcp isn't available
        class DummyFastMCP:
            def __init__(self, name):
                self.name = name
                self.tools = []

            def tool(self, name=None, description=None):
                def decorator(func):
                    self.tools.append(func)
                    return func

                return decorator

            def run(self):
                pass

        FastMCP = DummyFastMCP

    # Use a unique name for the server instance to ensure namespace isolation.
    import uuid

    server_name = f"mock_mcp_server_{uuid.uuid4().hex[:8]}"
    server = FastMCP(server_name)

    @server.tool()
    def mock_search(query: str) -> str:
        """Mock tool to search."""
        return f"Mock search result for {query}"

    @server.tool()
    def mock_calculator(a: int, b: int) -> int:
        """Mock tool to calculate sum."""
        return a + b

    return server


@pytest.fixture
def circuit_breaker(mock_llm_provider):
    """Fixture that kills tests exceeding a token threshold.

    To prevent runaway LLM costs or infinite loops during CI runs,
    this circuit breaker wraps the mock LLM provider's complete and acomplete
    methods. It raises a RuntimeError if the threshold is exceeded.
    """
    original_complete = mock_llm_provider.complete
    original_acomplete = mock_llm_provider.acomplete

    # Track the number of calls
    state = {"calls": 0, "token_threshold": 50}  # Simple mock representation

    def wrapped_complete(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] > state["token_threshold"]:
            raise RuntimeError(
                f"Circuit breaker triggered: Exceeded {state['token_threshold']} threshold"
            )
        return original_complete(*args, **kwargs)

    async def wrapped_acomplete(*args, **kwargs):
        state["calls"] += 1
        if state["calls"] > state["token_threshold"]:
            raise RuntimeError(
                f"Circuit breaker triggered: Exceeded {state['token_threshold']} threshold"
            )

        # We need to bypass wrapped complete here so we don't double count
        # because the original acomplete might call self.complete which is wrapped_complete
        orig_comp = mock_llm_provider.complete
        mock_llm_provider.complete = original_complete
        try:
            return await original_acomplete(*args, **kwargs)
        finally:
            mock_llm_provider.complete = orig_comp

    mock_llm_provider.complete = wrapped_complete
    mock_llm_provider.acomplete = wrapped_acomplete

    # Make threshold configurable on the fixture itself for tests that need it
    mock_llm_provider.set_circuit_breaker_threshold = lambda threshold: state.update(
        {"token_threshold": threshold}
    )

    yield mock_llm_provider

    # Restore original methods
    mock_llm_provider.complete = original_complete
    mock_llm_provider.acomplete = original_acomplete


@pytest.fixture
def memory_snapshot():
    """Fixture that captures STM state snapshots during node failures.

    Hooks into the GraphExecutor._write_progress method to intercept
    the state updates and extract the memory data. It allows tests to
    access the history of state snapshots, particularly useful for
    validating what the agent remembers right before or after a failure.
    """
    from framework.graph.executor import GraphExecutor

    original_write_progress = GraphExecutor._write_progress

    snapshots = []

    def patched_write_progress(self, current_node, path, memory, node_visit_counts):
        snapshots.append(
            {
                "current_node": current_node,
                "memory": memory,
                "path": list(path),
            }
        )
        original_write_progress(self, current_node, path, memory, node_visit_counts)

    GraphExecutor._write_progress = patched_write_progress

    yield snapshots

    GraphExecutor._write_progress = original_write_progress
