1. **Research** — Analyzed the issue related to token budget enforcement, reviewed \`GraphSpec\`, \`LoopConfig\`, \`EventLoopNode\`, \`Executor\`, and CLI code to find where modifications should occur. Found where `tokens_used` and `total_tokens` are populated.
2. **Core Logic**
    - Create `core/framework/graph/token_budget.py` with a thread-safe `TokenBudget` class. It will store total budget and accumulated tokens.
    - Modify `GraphSpec` in `core/framework/graph/edge.py` to add `token_budget: int | None = Field(default=None)`.
    - Modify `load_agent_export` in `core/framework/runner/runner.py` to populate `token_budget`.
    - Modify `LoopConfig` in `core/framework/graph/event_loop_node.py` to include `token_budget: int | None = None`.
    - Pass `token_budget` from `GraphSpec` to `EventLoopNode`'s `LoopConfig` in `executor.py` when instantiating `EventLoopNode`.
    - Integrate `TokenBudget` inside `EventLoopNode._execute_impl` (per-turn) and in `Executor` (after each node completes in `GraphExecutor.execute`). Stop execution or raise an exception when the budget is exceeded, and warn at 80%.
    - Add `--max-tokens` CLI argument to `core/framework/runner/cli.py` in `run_parser` and `shell_parser`.
3. **Validation** — Add unit tests in `core/framework/graph/tests/test_token_budget.py` and `test_executor_budget.py`, testing CLI, budget checking logic, warnings at 80%, etc.
4. **Documentation** — Add docstrings for `TokenBudget`, `GraphSpec.token_budget`, and `LoopConfig.token_budget` and mention the feature in `--max-tokens` CLI help string.
