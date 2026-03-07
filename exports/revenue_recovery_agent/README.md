# Revenue Recovery Agent

An e-commerce revenue recovery agent that monitors abandoned carts, failed payments, and lapsed buyers, then generates and sends personalized win-back sequences with human-in-the-loop approval.

## Features

- **Multi-segment targeting**: Abandoned carts, failed payments, lapsed buyers
- **Customer segmentation**: By value tier, purchase history, engagement level
- **Personalized messaging**: Tone and content tailored to segment
- **Human-in-the-loop approval**: 100% operator approval before sending
- **Campaign tracking**: Results logging and recovery rate tracking
- **Shopify integration**: Direct API access to orders and customers

## Workflow

```
intake → data_intake → segmentation → personalization → approval → send → tracking
                                         ↑                        |
                                         +-------- feedback -------+
```

1. **Intake**: Gather campaign parameters from operator
2. **Data Intake**: Fetch orders and customers from Shopify
3. **Segmentation**: Segment customers by value and behavior
4. **Personalization**: Generate personalized recovery emails
5. **Approval**: Present messages for operator review
6. **Send**: Dispatch approved emails
7. **Tracking**: Log results and generate report

## Installation

### Prerequisites

- Python 3.11+
- Shopify store with API access
- Email provider (Resend or Gmail)

### Setup Credentials

```bash
# Set up Shopify credentials
export SHOPIFY_ACCESS_TOKEN="your-shopify-access-token"
export SHOPIFY_STORE_NAME="your-store-name"

# Set up email credentials (choose one)
export RESEND_API_KEY="your-resend-api-key"
export EMAIL_FROM="noreply@yourstore.com"

# Or for Gmail
export GOOGLE_ACCESS_TOKEN="your-google-oauth-token"
```

## Usage

### CLI

```bash
# Validate agent structure
cd core && PYTHONPATH=../exports uv run python -m revenue_recovery_agent validate

# Show agent info
cd core && PYTHONPATH=../exports uv run python -m revenue_recovery_agent info

# Run a campaign
cd core && PYTHONPATH=../exports uv run python -m revenue_recovery_agent run

# Interactive shell
cd core && PYTHONPATH=../exports uv run python -m revenue_recovery_agent shell

# Launch TUI
cd core && PYTHONPATH=../exports uv run python -m revenue_recovery_agent tui
```

### Via Hive

```bash
hive open
# Select "Revenue Recovery Agent" from the agent list
```

## Configuration

The agent uses these configurable parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `time_window_days` | How far back to look for candidates | 30 |
| `discount_threshold` | Minimum cart value for discount offer | $50 |
| `discount_percent` | Discount percentage to offer | 10% |
| `lapsed_days` | Days without purchase to be "lapsed" | 60 |

## Success Criteria

- Cart recovery rate >= 10% on triggered sequences
- Message personalization quality score >= 4/5
- 100% human approval before any outreach
- Failed payment recovery rate >= 20% within 72 hours

## Files

- `config.py` - Runtime configuration and metadata
- `agent.py` - Goal, nodes, edges, and agent class
- `nodes/__init__.py` - Node definitions
- `__main__.py` - CLI interface
- `mcp_servers.json` - MCP server configuration
- `tests/` - Test files

## License

MIT
