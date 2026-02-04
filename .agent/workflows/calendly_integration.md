---
description: Implement Calendly integration
---
1. Ensure we are on the main branch and up to date.
// turbo
2. Create and checkout a new branch 'calendly-integration' resetted to main.
3. Create the directory structure for `tools/src/aden_tools/tools/calendly_tool`.
4. Implement the Calendly client and tool functions in `tools/src/aden_tools/tools/calendly_tool/__init__.py`.
   - Implement `get_current_user` to get user URI.
   - Implement `list_event_types` to get available event types.
   - Implement `create_scheduling_link` to generate a booking link.
   - Use `aden_tools.credentials` for API key management.
5. Create unit tests in `tools/tests/tools/test_calendly_tool.py`.
6. Run the tests to verify implementation.
7. Add documentation to `tools/README.md`.
