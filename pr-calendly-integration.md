Implement Calendly Integration

# Description
Implements Calendly integration for the Hive agent framework to enable automated scheduling workflows.

## Features
- List available event types for a user
- Create single-use scheduling links
- Integration with credential management system
- MCP tool registration

## Tools Added
- `calendly_list_event_types`: Lists available meeting types
- `calendly_create_scheduling_link`: Generates booking URLs

## Testing
- Unit tests added in `tools/tests/tools/test_calendly_tool.py`
- Verified using `pytest` in `agents` environment

## Related Issue
- Addresses issue #2930
