[Integration]: n8n – workflow automation (trigger and status) #2931

# Description
Implements the n8n integration for the Hive agent framework. This integration allows agents to trigger n8n workflows, check their execution status, and list available workflows. This enables seamless transitions between agent decision-making and business process automation.

## Features
- **Trigger Workflows**: Execute n8n workflows by ID with a custom JSON payload.
- **Execution Monitoring**: Retrieve real-time status (success, failed, running) for any execution.
- **Workflow Discovery**: List all workflows available on the n8n instance to allow agents to find the correct trigger.
- **Unified Credential Management**: Uses `CredentialManager` for secure storage of API keys and host URLs.

## Tools Added
- `n8n_trigger_workflow`: Triggers a workflow execution by ID.
- `n8n_get_execution_status`: Checks the status of a specific execution ID.
- `n8n_list_workflows`: Lists all available workflows for discovery.

## Environment Setup
| Variable | Description |
| --- | --- |
| `N8N_API_KEY` | Public API key from n8n instance settings. |
| `N8N_HOST` | The base URL of your n8n instance (e.g., `https://n8n.yourdomain.com`). |

## Testing
- Unit tests implemented in `tools/tests/tools/test_n8n_tool.py`.
- Tested success scenarios, API errors (401, 404, etc.), network timeouts, and MCP registration.
- Verified in the `agents` conda environment.

## Related Issue
- Resolve #2931
