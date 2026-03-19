content = """## Description

This PR fixes the Execution Limit Bypass via Session Resumption ("Infinite Gas" Glitch) vulnerability.

Previously, `GraphExecutor.execute` enforced a `max_steps` limit initializing it to zero upon each method call. When a graph node execution was paused (for HITL) or halted and later resumed via `session_state`, the `steps` counter was reset to 0, completely ignoring previously executed steps. This allowed malicious or malformed execution loops to bypass max_steps limits effectively giving infinite execution gas by continually pausing and resuming.

This PR updates `GraphExecutor` to initialize `steps = session_state.get("steps_executed", 0)` on resumption, and ensures all state-saving pathways (pause, failure, etc.) properly capture `"steps_executed": steps` into `session_state`.

## Type of Change

- [x] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

Resolves the reported Infinite Gas issue.

## Changes Made

- Updated `GraphExecutor.execute` to initialize `steps` variable from `session_state.get("steps_executed", 0)`.
- Updated pause generation logic to populate `"steps_executed": steps` into `pause_session_state`.
- Updated failure checkpoint generation to populate `"steps_executed": steps` into `failure_session_state`.
- Updated `session_state_out` generated during explicit pause nodes hit to also populate `"steps_executed": steps`.
- Added new verification test `test_executor_max_steps_resumption` inside `core/tests/test_graph_executor.py` asserting max_steps is preserved across manual pauses until termination.

## Testing

Describe the tests you ran to verify your changes:

- [x] Unit tests pass (`cd core && uv run pytest tests/`)
- [x] Lint passes (`cd core && uv run ruff check .`)
- [x] Manual testing performed (Ran newly added manual test directly to confirm steps resumption correctness).

## Checklist

- [x] My code follows the project's style guidelines
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] I have made corresponding changes to the documentation
- [x] My changes generate no new warnings
- [x] I have added tests that prove my fix is effective or that my feature works
- [x] New and existing unit tests pass locally with my changes

## Screenshots (if applicable)
"""
with open('.pr-3146.md', 'w') as f:
    f.write(content)
