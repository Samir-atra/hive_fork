# Issue Triage Agent

A cross-channel issue triage agent that ingests signals from GitHub Issues, Discord channels, and Gmail, normalizes and deduplicates reports, assigns category/severity/confidence with rationale, takes routing actions (GitHub labels, Discord acknowledgments, Gmail drafts), and produces clear operator-facing triage reports.

## What This Template Demonstrates

- **Multi-channel ingestion**: Fetching issues from GitHub, Discord, and Gmail simultaneously
- **Cross-channel deduplication**: Identifying and merging duplicate reports across platforms
- **Classification with rationale**: Assigning category, severity, and confidence with explanations
- **Safe routing actions**: GitHub labels (no auto-close), Discord acknowledgments, Gmail drafts (no auto-send)
- **Continuous triage loop**: Run repeated cycles with configurable policy adjustments

## Workflow

```
┌─────────┐     ┌──────────────┐     ┌─────────────────┐     ┌────────┐
│  Intake │ ──► │ Fetch Signals│ ──► │ Triage & Route  │ ──► │ Report │
└─────────┘     └──────────────┘     └─────────────────┘     └────────┘
     ▲                                                        │
     └────────────────────────────────────────────────────────┘
                    (rerun / adjust policy loop)
```

### Nodes

1. **Intake** (client-facing): Collect triage scope and policy from the operator
   - Sources to monitor (GitHub repo, Discord channel, Gmail query)
   - Severity threshold (P0/P1/P2/P3)
   - Categories to track
   - Auto-acknowledgment preferences

2. **Fetch Signals** (autonomous): Fetch issue signals from all configured sources
   - GitHub: List open issues from specified repository
   - Discord: Get recent messages from specified channel
   - Gmail: Search for matching support emails
   - Normalize and deduplicate across channels

3. **Triage and Route** (autonomous): Classify issues and take routing actions
   - Classify by category (bug, feature, security, etc.)
   - Assign severity (P0-P3) with rationale
   - Take safe routing actions:
     - GitHub: Add labels (never auto-close)
     - Discord: Send acknowledgment messages
     - Gmail: Create draft replies (never auto-send)

4. **Report** (client-facing): Present triage report and handle next actions
   - Summary by severity and category
   - List urgent issues (P0/P1) with details
   - Actions taken summary
   - Options: rerun, view details, adjust policy, or done

## Safety Constraints

- **GitHub Issues**: Never auto-close issues - only add labels or comments
- **Gmail**: Never send emails automatically - create drafts only for review
- **Classification**: Always include rationale for severity decisions

## Required Integrations

| Platform | Tools Used | Purpose |
|----------|------------|---------|
| GitHub | `github_list_issues`, `github_get_issue`, `github_update_issue` | Fetch and label issues |
| Discord | `discord_get_messages`, `discord_get_channel`, `discord_send_message` | Fetch and acknowledge messages |
| Gmail | `gmail_list_messages`, `gmail_get_message`, `gmail_create_draft` | Fetch and draft replies |

## Usage

### Option 1: Build from Template (recommended)

Use the `coder-tools` `initialize_and_build_agent` tool and select "From a template" to interactively pick this template, customize the goal/nodes/graph, and export a new agent.

### Option 2: Manual Copy

```bash
# 1. Copy to your exports directory
cp -r examples/templates/issue_triage_agent exports/my_triage_agent

# 2. Update the module references in __main__.py and __init__.py

# 3. Customize goal, nodes, edges, and prompts

# 4. Run it
cd core && uv run python -m exports.my_triage_agent --input '{}'
```

### Option 3: Direct Run

```bash
cd core && uv run python -m examples.templates.issue_triage_agent
```

## Configuration

Before running, ensure you have configured the required credentials:

1. **GitHub**: Set `GITHUB_TOKEN` environment variable or configure via hive.adenhq.com
2. **Discord**: Set `DISCORD_BOT_TOKEN` environment variable or configure via hive.adenhq.com
3. **Gmail**: Connect your Google account via hive.adenhq.com for OAuth2 access

## Customization Ideas

- Add Slack integration for additional channel support
- Integrate with Linear or Jira for issue tracking
- Add automatic escalation rules for P0 issues
- Include sentiment analysis for angry/frustrated users
- Add team member routing based on issue category
