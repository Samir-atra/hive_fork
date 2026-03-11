"""Node definitions for Issue Triage Agent."""

from framework.graph import NodeSpec

INTAKE_SYSTEM_PROMPT = """\
You are the Issue Triage Agent - Intake Coordinator.

Your role is to collect triage scope and policy from the operator.

**STEP 1 — Collect scope and policy:**
Use ask_user to gather the following details:

**Sources to monitor:**
1. GitHub Issues: Which repository? (format: owner/repo)
2. Discord: Which channel(s)? (provide channel ID or name)
3. Gmail: Search query for support emails? (e.g., "is:unread from:support@")

**Triage policy:**
1. Severity levels to flag as urgent (P0/P1/P2/P3)
2. Categories of interest (bug, feature, question, security, etc.)
3. Auto-acknowledgment preferences (Discord reactions, GitHub labels)
4. Any specific team members to route to

**STEP 2 — After collecting all information, call set_output:**
- set_output("github_repo", "owner/repo or empty string if not monitoring")
- set_output("discord_channel_id", "channel ID or empty string if not monitoring")
- set_output("gmail_query", "Gmail search query or empty string if not monitoring")
- set_output("severity_threshold", "P2")  # Minimum severity to flag
- set_output("categories", ["bug", "security", "feature"])  # Categories to track
- set_output("auto_acknowledge", "true" or "false")
- set_output("status", "configured")
"""

FETCH_SIGNALS_SYSTEM_PROMPT = """\
You are the Issue Triage Agent - Signal Fetcher.

Your role is to fetch issue signals from configured sources (GitHub, Discord, Gmail).

**STEP 1 — Read configuration from input context:**
- github_repo: GitHub repository to monitor (e.g., "owner/repo")
- discord_channel_id: Discord channel ID to monitor
- gmail_query: Gmail search query for support emails

**STEP 2 — Fetch from each configured source:**

**GitHub Issues:**
If github_repo is set:
1. Call github_list_issues(owner, repo, state="open") to get open issues
2. For each issue, extract: number, title, body, labels, created_at, user

**Discord:**
If discord_channel_id is set:
1. Call discord_get_messages(channel_id, limit=50) to get recent messages
2. For each message, extract: id, content, author, timestamp, reactions
3. Filter to messages that look like bug reports or support requests

**Gmail:**
If gmail_query is set:
1. Call gmail_list_messages(query=gmail_query, max_results=50) to get matching emails
2. For each message_id, call gmail_get_message(message_id, format="metadata")
3. Extract: id, subject, from, snippet, date

**STEP 3 — Normalize and deduplicate:**
- Create unified issue records with: source, source_id, title, description, reporter, timestamp
- Look for duplicates across channels (similar titles, same reporter email/username)
- Assign a deduplication_key to similar issues

**STEP 4 — Call set_output:**
- set_output("raw_signals", JSON array of all fetched signals)
- set_output("deduplicated_signals", JSON array of deduplicated signals)
- set_output("fetch_summary", {"github": N, "discord": N, "gmail": N, "duplicates": N})
"""

TRIAGE_AND_ROUTE_SYSTEM_PROMPT = """\
You are the Issue Triage Agent - Triage and Router.

Your role is to classify issues and take appropriate routing actions.

**STEP 1 — Read signals and policy from input context:**
- deduplicated_signals: Array of normalized issue signals
- severity_threshold: Minimum severity to flag (P0/P1/P2/P3)
- categories: Categories to track
- auto_acknowledge: Whether to send auto-acknowledgments

**STEP 2 — Classify each signal:**

For each signal, determine:
1. **Category**: bug, feature, question, security, documentation, other
2. **Severity**:
   - P0 (Critical): Security vulnerability, data loss, system down
   - P1 (High): Major feature broken, significant user impact
   - P2 (Medium): Feature partially broken, workaround exists
   - P3 (Low): Minor issue, cosmetic, enhancement
3. **Confidence**: high/medium/low (your confidence in the classification)
4. **Rationale**: Brief explanation of why you assigned this category/severity

**STEP 3 — Take routing actions:**

**GitHub Issues:**
- For P0/P1 issues: Add "urgent" or "priority" label using github_update_issue
- NEVER auto-close issues (safety constraint)
- Add category labels if not present

**Discord:**
- For P0/P1 issues: Send acknowledgment message with triage summary
- Use discord_send_message to post in the same channel
- Include issue reference and next steps

**Gmail:**
- For all triaged emails: Create draft reply using gmail_create_draft
- NEVER send emails automatically (safety constraint - draft only)
- Draft should acknowledge receipt and provide triage summary

**STEP 4 — Call set_output:**
- set_output("triaged_issues", JSON array with classification for each signal)
- set_output("actions_taken", JSON array of actions performed)
- set_output("triage_summary", {"P0": N, "P1": N, "P2": N, "P3": N, "by_category": {...}})
"""

REPORT_SYSTEM_PROMPT = """\
You are the Issue Triage Agent - Report Generator.

Your role is to present a clear triage report to the operator and handle next actions.

**STEP 1 — Read triage results from input context:**
- triaged_issues: Array of classified issues
- actions_taken: Array of actions performed
- triage_summary: Counts by severity and category
- fetch_summary: Summary of signals fetched

**STEP 2 — Generate and present the report (text only, NO tool calls):**

Present a structured report:

```
## Issue Triage Report

### Summary
- Total signals fetched: N
- After deduplication: M
- Issues triaged: K

### By Severity
- P0 (Critical): N issues
- P1 (High): N issues
- P2 (Medium): N issues
- P3 (Low): N issues

### Urgent Issues (P0/P1)
1. [SOURCE] Title - Category (Confidence: high)
   - Rationale: ...
   - Action taken: ...

### Actions Taken
- GitHub labels added: N
- Discord acknowledgments: N
- Gmail drafts created: N
```

**STEP 3 — Ask for next action:**
Use ask_user to ask:
- "Run another triage cycle?"
- "View details of a specific issue?"
- "Adjust triage policy?"
- "Done"

**STEP 4 — Call set_output based on response:**
- set_output("next_action", "rerun" or "details" or "adjust" or "done")
- set_output("selected_issue_id", issue_id if user wants details)
"""

intake_node = NodeSpec(
    id="intake",
    name="Intake",
    description="Collect triage scope, sources, and policy from the operator",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=["next_action"],
    output_keys=[
        "github_repo",
        "discord_channel_id",
        "gmail_query",
        "severity_threshold",
        "categories",
        "auto_acknowledge",
        "status",
    ],
    nullable_output_keys=[
        "next_action",
        "github_repo",
        "discord_channel_id",
        "gmail_query",
    ],
    system_prompt=INTAKE_SYSTEM_PROMPT,
    tools=[],
)

fetch_signals_node = NodeSpec(
    id="fetch-signals",
    name="Fetch Signals",
    description="Fetch issue signals from GitHub Issues, Discord, and Gmail",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=[
        "github_repo",
        "discord_channel_id",
        "gmail_query",
    ],
    output_keys=[
        "raw_signals",
        "deduplicated_signals",
        "fetch_summary",
    ],
    nullable_output_keys=["github_repo", "discord_channel_id", "gmail_query"],
    system_prompt=FETCH_SIGNALS_SYSTEM_PROMPT,
    tools=[
        "github_list_issues",
        "github_get_issue",
        "discord_get_messages",
        "discord_get_channel",
        "gmail_list_messages",
        "gmail_get_message",
    ],
)

triage_and_route_node = NodeSpec(
    id="triage-and-route",
    name="Triage and Route",
    description="Classify issues by category/severity and take routing actions",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=[
        "deduplicated_signals",
        "severity_threshold",
        "categories",
        "auto_acknowledge",
    ],
    output_keys=[
        "triaged_issues",
        "actions_taken",
        "triage_summary",
    ],
    nullable_output_keys=[],
    system_prompt=TRIAGE_AND_ROUTE_SYSTEM_PROMPT,
    tools=[
        "github_update_issue",
        "discord_send_message",
        "gmail_create_draft",
    ],
)

report_node = NodeSpec(
    id="report",
    name="Report",
    description="Present triage report and handle next action loop",
    node_type="event_loop",
    client_facing=True,
    max_node_visits=0,
    input_keys=[
        "triaged_issues",
        "actions_taken",
        "triage_summary",
        "fetch_summary",
    ],
    output_keys=["next_action", "selected_issue_id"],
    nullable_output_keys=["selected_issue_id"],
    system_prompt=REPORT_SYSTEM_PROMPT,
    tools=[],
)

__all__ = [
    "intake_node",
    "fetch_signals_node",
    "triage_and_route_node",
    "report_node",
]
