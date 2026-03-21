plan = """1. **Research**
   - The issue requests implementing a `ShadowExecutor` to safely test graph evolution in shadow mode.
   - Based on project memories, `HybridJudge` was removed during Phase 2 cleanup. Instead, I need to "implement the requested functionality by adapting it to the current architecture (e.g., mapping \`HybridJudge\` features to \`ConversationJudge\` and \`EventLoopNode\`)".
   - The issue requires running two `GraphSpec`s (a baseline and a candidate) against the same input.
   - The outputs (`ExecutionResult`) are compared to evaluate the candidate against the baseline.
   - The comparison criteria includes: success/failure, execution quality (via an LLM judge evaluating against the `Goal`), token cost, and latency.
   - The framework uses `EventBus`, and a new event `SHADOW_COMPARISON_COMPLETED` needs to be added.

2. **Core Logic**
   - **`core/framework/runtime/event_bus.py`**:
     - Add `SHADOW_COMPARISON_COMPLETED = "shadow_comparison_completed"` to the `EventType` Enum.
     - Add an async method `emit_shadow_comparison_completed(...)` to the `EventBus` class to emit this new event.
   - **`core/framework/graph/shadow_executor.py`** (New file):
     - Define a `ShadowComparisonResult` dataclass containing `winner` ("baseline", "candidate", or "tie"), `should_promote` (bool), `baseline_result` (ExecutionResult), `candidate_result` (ExecutionResult), and `metrics` (dict).
     - Define `VersionComparator` which takes an `LLMProvider` and a `Goal`, and compares two `ExecutionResult`s. It uses an LLM to judge quality (similar to `evaluate_phase_completion` in `ConversationJudge`), then considers latency and tokens.
     - Define `ShadowExecutor` which accepts: `baseline` (GraphSpec), `candidate` (GraphSpec), `llm` (LLMProvider), `runtime` (Runtime), and an optional `confidence_threshold`.
     - Implement `ShadowExecutor.execute(goal, input_data, session_state)` which instantiates two `GraphExecutor`s.
     - The `GraphExecutor` instances must run with isolated memory. We will achieve this by giving them unique `stream_id`s or ensuring `IsolationLevel.ISOLATED` is used.
     - Use `asyncio.gather` to execute both concurrently.
     - Use `VersionComparator` to evaluate the outputs.
     - Emit the `SHADOW_COMPARISON_COMPLETED` event via the `EventBus`.
     - Return the `ShadowComparisonResult`.
   - **`core/framework/graph/__init__.py`**:
     - Export `ShadowExecutor` and `ShadowComparisonResult`.

3. **Validation**
   - **Unit Tests**:
     - Create `core/tests/test_shadow_executor.py` to verify the execution of both baseline and candidate graphs in parallel using `ShadowExecutor`.
     - Mock the `GraphExecutor`'s execute method and `LLMProvider` to ensure the logic in `VersionComparator` functions correctly, applying the confidence threshold.
     - Ensure the `SHADOW_COMPARISON_COMPLETED` event is emitted correctly on the runtime's event bus.
   - **Commands**:
     - Run `cd core && uv run pytest tests/test_shadow_executor.py`.
     - Run the full test suite `cd core && uv run pytest tests/`.
     - Run `cd core && uv run ruff check .` and format.

4. **Documentation**
   - Add docstrings to all new modules, classes, and methods using the Google docstring style.
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done."""
