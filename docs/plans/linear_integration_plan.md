# implementation Plan - Linear Integration (Issue #2859)

## 1. Goal
Implement a native `linear_tool` module providing:
1.  **Create Issue**: Allow agents to report bugs/features directly to a specific Team/Project.
2.  **Get Issue**: Fetch issue details/status by ID.
3.  **Search**: Query issues using Linear's filtering syntax.

## 2. Core Logic
- **Directory**: `tools/src/aden_tools/tools/linear_tool/`
- **File**: `linear_tool.py`
- **Class**: `_LinearClient` (internal helper)
    - Authentication via `LINEAR_API_KEY` environment variable.
    - `_execute_query(query, variables)` method using `httpx.post` to `https://api.linear.app/graphql`.
- **Tools**:
    - `linear_create_issue(title, team_id, description=None, priority=None, state_id=None, assignee_id=None)`
        - Uses `issueCreate` mutation.
    - `linear_get_issue(issue_id)`
        - Uses `issue` query.
    - `linear_search_issues(query, limit=10)`
        - Uses `issueSearch` query.

## 3. Validation
- **Unit Tests**: `tools/tests/test_linear_tool.py`
    - Mock `httpx.post` to simulate Linear API responses.
    - Test success and error scenarios (auth failure, validation error).
    - Helper function to mock GraphQL responses.

## 4. Documentation
- **README.md**: Create `tools/src/aden_tools/tools/linear_tool/README.md` with setup instructions (API Key) and usage examples.
- **Index**: Update `tools/TOOLS_INDEX.md` (if applicable, though auto-generation might handle this later).

## 5. Dependencies
- No new dependencies. Uses `httpx` and standard library.
