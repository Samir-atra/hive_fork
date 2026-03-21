plan = """
1. **Core Logic 1: Create Conftest Base**
   - Create `core/tests/agents/conftest.py` with base fixtures: `mock_llm_provider` (using `framework.llm.mock.MockLLMProvider` which requires no real LLM calls) and `agent_builder` (a helper method that takes nodes/edges and returns a GraphExecutor).

2. **Core Logic 2: Add MCP Mock and Circuit Breaker**
   - Add the `mock_mcp_server` fixture to `core/tests/agents/conftest.py`. It returns a mock FastMCP configuration using `from mcp.server import FastMCP`.
   - Add the `circuit_breaker` fixture to `core/tests/agents/conftest.py` that intercepts `MockLLMProvider` calls and raises a `RuntimeError` if a specified token limit (e.g. 50 calls) is exceeded.

3. **Core Logic 3: Add Memory Snapshot**
   - Add the `memory_snapshot` fixture to `core/tests/agents/conftest.py` that intercepts `framework.graph.executor.GraphExecutor._write_progress` to capture `memory` state snapshots during execution.

4. **Validation 1: Verify Conftest**
   - Run `cd core && uv run ruff check tests/agents/conftest.py` to verify the syntax of the fixtures.

5. **Validation 2: Implement Test Functions**
   - Create `core/tests/agents/test_sample_agent.py` using these fixtures:
     - `test_node_schema_validation`: Validates that a node schema can be validated.
     - `test_agent_graph_execution`: Executes a simple mock agent graph.
     - `test_circuit_breaker_halts_execution`: Asserts the `circuit_breaker` halts execution.
     - `test_memory_snapshot_on_failure`: Asserts `memory_snapshot` successfully captures STM on failure.

6. **Validation 3: Run Tests**
   - Run `cd core && uv run pytest tests/agents/` and verify the output. If failing, fix and verify again.

7. **Validation 4: Run Full Test Suite**
   - Run the full test suite using `cd core && uv run pytest tests/` to ensure no regressions.

8. **Documentation 1: Create CI Workflow**
   - Create `ci/agent-tests.yml` to run the agent test harness automatically using GitHub Actions.

9. **Documentation 2: Verify CI Workflow**
   - Use `cat` to verify the content of `ci/agent-tests.yml`.

10. **Pre Commit Checks**
    - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.

11. **Create PR Description**
    - Create the `.pr-3803.md` file following the template from the issue instructions.

12. **Commit Changes**
    - Run `git add core/tests/agents/conftest.py core/tests/agents/test_sample_agent.py ci/agent-tests.yml` and `git commit -m "feat: Add CI-friendly agent test harness — closes #3803"`.

13. **Push Changes**
    - Run `git pull --rebase` followed by `git push`.

14. **Submit PR**
    - Run the `ghapi` Python script to open the Pull Request on the user's fork targeting the main branch.
"""
print(plan)
