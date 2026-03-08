# Hacker News Briefing Agent

**Version**: 1.0.0
**Type**: Multi-node agent with feedback loop
**Created**: 2026-03-08

## Overview

Collects top Hacker News stories daily, ranks them by relevance and value, produces a concise briefing with "why it matters" notes and source links, and delivers via user-configurable channels (markdown, email, slack).

## Architecture

### Execution Flow

```
intake-preferences -> collect-hn-candidates -> rank-and-summarize -> review-briefing -> deliver-briefing
                                              ^                          |
                                              +--------- (revise) --------+
```

### Nodes (5 total)

1. **intake-preferences** (event_loop, client-facing)
   - Collect user preferences for delivery channel, timezone, focus areas, and story count.
   - Writes: `briefing_config`
   - Client-facing: Yes (blocks for user input)

2. **collect-hn-candidates** (event_loop)
   - Scrape Hacker News front page and collect top story candidates with metadata.
   - Reads: `briefing_config`
   - Writes: `hn_candidates`
   - Tools: `web_scrape`

3. **rank-and-summarize** (event_loop)
   - Rank stories by relevance and engagement, create summaries with "why it matters" notes.
   - Reads: `briefing_config`, `hn_candidates`
   - Writes: `ranked_briefing`

4. **review-briefing** (event_loop, client-facing)
   - Present briefing preview to user, allow approval or revision requests.
   - Reads: `briefing_config`, `ranked_briefing`
   - Writes: `review_status`, `revision_feedback` (nullable)
   - Client-facing: Yes (blocks for user input)

5. **deliver-briefing** (event_loop, client-facing)
   - Deliver final briefing via configured channel(s).
   - Reads: `briefing_config`, `ranked_briefing`, `review_status`
   - Writes: `delivery_result`
   - Tools: `save_data`, `append_data`, `serve_file_to_user`
   - Client-facing: Yes

### Edges (5 total)

- `intake-preferences` → `collect-hn-candidates` (condition: on_success, priority=1)
- `collect-hn-candidates` → `rank-and-summarize` (condition: on_success, priority=1)
- `rank-and-summarize` → `review-briefing` (condition: on_success, priority=1)
- `review-briefing` → `deliver-briefing` (condition: conditional, when status="approved", priority=1)
- `review-briefing` → `rank-and-summarize` (condition: conditional, when status="revise", priority=2) — **feedback loop**

## Goal Criteria

### Success Criteria

**Collects top HN stories with metadata** (weight 0.2)
- Metric: stories_collected
- Target: >=5

**Ranks stories by relevance and community engagement** (weight 0.2)
- Metric: ranking_quality
- Target: true

**Provides concise summaries with "why it matters" notes** (weight 0.2)
- Metric: summaries_provided
- Target: 100%

**Allows user to review and refine the briefing** (weight 0.15)
- Metric: user_reviewed
- Target: true

**Delivers briefing via configured channel(s)** (weight 0.25)
- Metric: delivered
- Target: true

### Constraints

**Never fabricate stories or URLs** (hard)
- Category: quality

**Always include source links for every story** (hard)
- Category: quality

**Always deliver via markdown at minimum** (hard)
- Category: reliability

**Keep summaries brief and actionable** (soft)
- Category: quality

## Required Tools

- `web_scrape` — for collecting HN stories
- `save_data` — for creating the briefing file
- `append_data` — for building the file in chunks
- `serve_file_to_user` — for delivering the briefing

## Delivery Channels

The agent supports multiple delivery channels:

1. **markdown** (default, no setup required)
   - Creates a formatted markdown file
   - Served via `serve_file_to_user`

2. **email** (requires credentials)
   - Sends HTML email with the briefing
   - Requires email configuration

3. **slack** (requires credentials)
   - Posts to Slack channel
   - Requires Slack webhook configuration

4. **all**
   - Attempts delivery via all configured channels
   - Falls back to markdown for unconfigured channels

## Usage

### Basic Usage

```python
from framework.runner import AgentRunner

# Load the agent
runner = AgentRunner.load("examples/templates/hacker_news_briefing")

# Run with input
result = await runner.run({})

# Access results
print(result.output)
print(result.status)
```

### CLI Usage

```bash
# Run the agent
python -m examples.templates.hacker_news_briefing run

# Show agent info
python -m examples.templates.hacker_news_briefing info

# Validate agent structure
python -m examples.templates.hacker_news_briefing validate

# Interactive shell
python -m examples.templates.hacker_news_briefing shell
```

### Input Schema

The agent's entry node `intake-preferences` accepts initial context but primarily collects preferences via user interaction.

### Output Schema

Terminal node: `deliver-briefing`

Output includes:
- `delivery_result`: JSON with delivery status, channels used, and file path

## Version History

- **1.0.0** (2026-03-08): Initial release
  - 5 nodes, 5 edges (including feedback loop)
  - Goal: Hacker News Briefing
  - Supports configurable delivery channels
  - Human-in-the-loop review with revision capability
