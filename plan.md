1. **Research**
   - The issue (#3551) states that `register_node()` in `core/framework/graph/executor.py` accepts any object without validation, causing cryptic runtime errors when an invalid object is registered as a node implementation.
   - We need to validate the `implementation` parameter passed to `GraphExecutor.register_node()`.
   - Based on the expected behavior described in the issue, we should:
     - Check if the implementation is `None` and raise `ValueError("Cannot register None as node")`.
     - Check if it implements `NodeProtocol`.
     - Check if its `execute` method is an async method using `inspect.iscoroutinefunction(getattr(implementation, "execute", None))`.
     - If it's not a valid implementation, raise `ValueError("Node must implement NodeProtocol with async execute() method")`.

2. **Core Logic**
   - File: `core/framework/graph/executor.py`
   - Method: `GraphExecutor.register_node()`
   - Changes: Add validation at the beginning of the `register_node` method:
     ```python
     def register_node(self, node_id: str, implementation: NodeProtocol) -> None:
         """Register a custom node implementation."""
         if implementation is None:
             raise ValueError("Cannot register None as node")

         if not isinstance(implementation, NodeProtocol):
             raise ValueError("Node must implement NodeProtocol with async execute() method")

         execute_method = getattr(implementation, "execute", None)
         if not execute_method or not inspect.iscoroutinefunction(execute_method):
             raise ValueError("Node must implement NodeProtocol with async execute() method")

         self.node_registry[node_id] = implementation
     ```

3. **Validation**
   - Ensure the new file `core/tests/framework/graph/test_invalid_node_types.py` accurately catches these scenarios.
   - Specifically verify that `None`, ints, strings, objects without `execute`, and objects with a synchronous `execute` raise the expected `ValueError`.
   - Run the full test suite in `core/` to ensure no regressions using `cd core && uv run pytest tests/`.

4. **Documentation**
   - No README files need to be updated.
   - The `register_node` docstring may be updated to reflect that it raises `ValueError` if the implementation is invalid, following the Google docstring style.
