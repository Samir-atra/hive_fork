1. **Research**
   - We need to implement a new `ShadowExecutor` that will run two `GraphSpec` (a candidate and a baseline) on the same input using `GraphExecutor` isolated state.
   - It will use `HybridJudge` to compare the two outputs. Wait, I cannot find `HybridJudge` in the codebase. I need to look closely for how evaluation is done. Let me check `ConversationJudge`, `SubagentJudge` or `JudgeProtocol`.
   - The issue specifies `HybridJudge` evaluates one result against a goal... "HybridJudge evaluates one result against a goal, but cannot compare two results side by side". Let me search again to see if there is any mention of `HybridJudge` anywhere. It could be an hallucination in the issue description or perhaps it was renamed. If there is no `HybridJudge`, I should probably implement the comparison logic inside a `VersionComparator` or simply a `evaluate_shadow_comparison` function using the `LLMProvider` directly similar to `ConversationJudge`, evaluating the two `ExecutionResult`s.
   - I need to add an event `SHADOW_COMPARISON_COMPLETED` to `EventType`.
   - The `ShadowExecutor` should receive baseline and candidate graphs, an optional judge (or I can just use an LLM provider to evaluate them), run them in parallel (using `asyncio.gather`), collect `ExecutionResult`s, and then compare them.
   - The output of `ShadowExecutor.execute` will be a `ShadowComparisonResult` containing winner, should_promote, etc.

Let me search for Judge or Evaluation classes again.
