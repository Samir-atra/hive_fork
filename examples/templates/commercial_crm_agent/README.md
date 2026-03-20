# Commercial CRM Agent

A "Revenue/Support Agent" that bridges a CRM system (like HubSpot or Salesforce) with a team messaging platform (like Slack or Teams).

This template aims to minimize the "integration tax" by providing a zero-glue-code approach. It takes a natural language intent, searches the CRM for leads/deals using MCP tools, and dispatches formatted alerts directly to the team's messaging channels.

## Requirements

You must provide the necessary API keys or tokens for the tools configured in `mcp_servers.json`. For example, you may need:
- `HUBSPOT_ACCESS_TOKEN` for the HubSpot server
- `SLACK_BOT_TOKEN` and `SLACK_TEAM_ID` for the Slack server

These can be provided via environment variables or standard `.env` configuration.

## Graph Structure

The agent operates in a 3-step loop:

1. **Intake** (Client-Facing)
   - Gets the user's intent. Extracts the CRM filter (e.g., "leads not contacted in 3 days") and the messaging channel (e.g., "#sales-alerts").
2. **CRM Search** (Autonomous)
   - Executes MCP tool queries against the configured CRM based on the parsed intent.
3. **Messaging Notification** (Autonomous)
   - Formats the retrieved CRM records into a clear message and dispatches it to the requested messaging destination.

## How to use

1. Add your tool credentials to the environment.
2. Edit `mcp_servers.json` to suit your specific CRM and messaging platforms.
3. Run the agent using the standard CLI:

```bash
uv run python -m examples.templates.commercial_crm_agent --query "Find leads uncontacted for 3 days" --channel "#sales-alerts"
```
