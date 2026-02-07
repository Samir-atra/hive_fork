[Integration]: Discord – channels and messages

# Description
Implements Discord integration for the Hive agent framework. This integration enables agents to manage Discord channels and send messages, facilitating real-time notifications, alerts, and community engagement directly from agent workflows.

## Features
- **Channel Listing**: List all channels in a specific guild (server) to discover where to post.
- **Messaging**: Send text messages to any channel by ID.
- **History**: Retrieve recent messages from a channel to understand context or check for updates.
- **Secure Authentication**: Uses Bot Token via `CredentialManager`.

## Tools Added
- `discord_list_channels`: List channels in a guild.
- `discord_send_message`: Send a message to a channel.
- `discord_get_recent_messages`: Get recent messages from a channel.

## Environment Setup
| Variable | Description |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot Token from the Developer Portal. |

## Use Cases
- **Incident Management**: Post incident summaries to #incidents channel when resolved.
- **Alerting**: Notify dev teams of deployment status or system alerts.
- **Community Engagement**: Agents can participate in specific channel discussions.

## Testing
- Unit tests coverage for client initialization, message sending, channel listing, and history retrieval.
- Verified error handling for invalid tokens and API errors.

## Related Issue
- Resolve #2913
