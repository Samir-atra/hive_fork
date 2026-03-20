1. **Research**
   - The user wants a `hive demo` command.
   - It should use a pre-built agent graph with a deterministic mock LLM, and run locally without requiring API keys.
   - It should demonstrate: goal-based success evaluation, constraints, and decision logging.
   - `MockLLMProvider` currently generates simple text like "mock_result_value".
   - We need a `ScriptableMockLLMProvider` or something similar so we can provide realistic scripted responses for the demo. I can just subclass `LLMProvider` locally in the demo module or create a scripted provider.

2. **Core Logic**
   - Create `core/framework/runner/demo.py`.
   - Implement `DemoMockLLMProvider(LLMProvider)` inside `demo.py` that yields realistic pre-scripted JSON responses (e.g. calling tools, providing a final answer).
   - Define a simple agent programmatically inside `demo.py`:
     - Goal: "Calculate the sum of 5 and 7, and verify it's even."
     - Tool: `add(a: int, b: int) -> int`
     - Constraints: "The result must be an even number."
     - Node: `EventLoopNode` or `FunctionNode` (Wait, FunctionNode is deprecated, use `EventLoopNode`).
   - `cmd_demo(args)` logic:
     - Print welcome message.
     - Build the Graph, Goal, and nodes.
     - Instantiate `AgentRunner` manually (or bypass `load` and set it up manually to inject the DemoMockLLMProvider).
     - Run the agent.
     - Print the steps beautifully with colors (using `print` with ANSI escapes or rich if it's available).

3. **Validation**
   - Add a test `core/tests/test_cli_demo.py` that verifies `cmd_demo` executes fully and correctly.
   - Run existing tests to ensure no regressions.

4. **Documentation**
   - Add a brief section in `README.md` introducing `hive demo`.
