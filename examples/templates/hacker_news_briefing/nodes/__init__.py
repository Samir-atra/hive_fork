"""Node definitions for Hacker News Briefing agent."""

from framework.graph import NodeSpec

intake_preferences_node = NodeSpec(
    id="intake-preferences",
    name="Intake Preferences",
    description=(
        "Collect user preferences for delivery channel, timezone, and briefing focus areas."
    ),
    node_type="event_loop",
    client_facing=True,
    input_keys=[],
    output_keys=["briefing_config"],
    system_prompt="""\
You are the intake assistant for a Hacker News Briefing agent.

**STEP 1 — Greet and ask for preferences:**
Greet the user and ask about their briefing preferences. Collect:

1. **Delivery Channel**: How would they like to receive the briefing?
   - markdown (default, no setup required)
   - email (requires email configuration)
   - slack (requires Slack webhook)
   - all (delivers via all configured channels)

2. **Timezone**: What timezone should the briefing be timestamped in?
   (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")

3. **Focus Areas** (optional): Are there specific topics they care about?
   - Technology startups
   - Programming languages
   - AI/ML
   - Security
   - General tech news
   - All (no filter)

4. **Number of stories**: How many top stories to include? (default: 10)

Keep it brief and conversational. Use ask_user() to wait for their response.

**STEP 2 — After the user responds, call set_output:**
- set_output("briefing_config", <JSON string>)

Output format:
```json
{
  "delivery_channel": "markdown",
  "timezone": "America/New_York",
  "focus_areas": ["AI/ML", "startups"],
  "story_count": 10
}
```

If the user doesn't specify something, use sensible defaults:
- delivery_channel: "markdown"
- timezone: "UTC"
- focus_areas: ["all"]
- story_count: 10
""",
    tools=[],
)

collect_hn_candidates_node = NodeSpec(
    id="collect-hn-candidates",
    name="Collect HN Candidates",
    description="Scrape Hacker News front page and collect top story candidates.",
    node_type="event_loop",
    input_keys=["briefing_config"],
    output_keys=["hn_candidates"],
    system_prompt="""\
You are a data collector for a Hacker News Briefing agent.

Your task: Collect the top stories from Hacker News.

**Instructions:**

1. Use web_scrape to fetch the Hacker News front page:
   - https://news.ycombinator.com
   - Set max_length=10000 and include_links=true

2. Parse the scraped content and extract:
   - Story titles
   - Story URLs (the actual article links, not HN discussion links)
   - HN discussion URLs (the "item?id=..." links)
   - Points/score
   - Number of comments
   - Rank position on the front page

3. Focus on the top N stories based on briefing_config.story_count (default: 10).
   If focus_areas is specified and not ["all"], prioritize stories matching those topics.

4. For each story, you may optionally scrape the actual article to get a brief snippet
   (max_length=2000 per article, only for top 5 stories to stay efficient).

**Output format:**
Use set_output("hn_candidates", <JSON string>) with this structure:
```json
{
  "stories": [
    {
      "title": "Story Title",
      "url": "https://actual-article-url.com/...",
      "hn_url": "https://news.ycombinator.com/item?id=...",
      "points": 342,
      "comments": 127,
      "rank": 1,
      "snippet": "Optional brief excerpt from the article...",
      "topic_hints": ["AI", "startups"]
    }
  ],
  "collected_at": "2026-03-08T10:30:00Z",
  "total_on_front_page": 30
}
```

**Rules:**
- Only include real stories with real URLs from the scraped content
- Never fabricate URLs or stories
- Copy URLs exactly as they appear in the scrape results
- If the front page fails to load, report an error in the output
""",
    tools=["web_scrape"],
)

rank_and_summarize_node = NodeSpec(
    id="rank-and-summarize",
    name="Rank and Summarize",
    description=(
        "Rank HN stories by relevance, create concise summaries with 'why it matters' notes."
    ),
    node_type="event_loop",
    input_keys=["briefing_config", "hn_candidates"],
    output_keys=["ranked_briefing"],
    system_prompt="""\
You are an editor for a Hacker News Briefing agent.

Your task: Rank the collected stories and create a concise, valuable briefing.

**Ranking Criteria:**
1. **Relevance**: Match to user's focus_areas (if specified)
2. **Engagement**: Higher points and comments indicate community interest
3. **Impact**: Stories that matter to tech professionals
4. **Recency**: Fresh news over older discussions

**Instructions:**

1. Review the hn_candidates stories.

2. Rank them by combining:
   - Points (community signal)
   - Comments (discussion depth)
   - Relevance to focus_areas
   - Your assessment of "why it matters" to a tech professional

3. For each story, write:
   - A one-sentence summary
   - A "Why it matters" note (1-2 sentences explaining the significance)
   - The relevance score (1-10)

4. Select the top N stories (based on briefing_config.story_count).

**Output format:**
Use set_output("ranked_briefing", <JSON string>) with this structure:
```json
{
  "briefing_date": "2026-03-08",
  "timezone": "America/New_York",
  "stories": [
    {
      "rank": 1,
      "title": "Story Title",
      "url": "https://...",
      "hn_url": "https://news.ycombinator.com/item?id=...",
      "points": 342,
      "comments": 127,
      "summary": "One sentence summary of the story.",
      "why_it_matters": "This matters because... (1-2 sentences)",
      "relevance_score": 9,
      "topic": "AI"
    }
  ],
  "total_candidates": 30,
  "selected_count": 10
}
```

**Rules:**
- Keep summaries concise and factual
- "Why it matters" should explain the significance to a tech professional
- Don't exaggerate or fabricate information
- If focus_areas was specified, prioritize matching stories
""",
    tools=[],
)

review_briefing_node = NodeSpec(
    id="review-briefing",
    name="Review Briefing",
    description="Present the briefing to the user for review and allow refinement.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["briefing_config", "ranked_briefing"],
    output_keys=["review_status"],
    nullable_output_keys=["revision_feedback"],
    system_prompt="""\
You are the review coordinator for a Hacker News Briefing agent.

Your task: Present the briefing to the user and get their feedback.

**STEP 1 — Present the briefing:**
Show the user a preview of their briefing with:
- Number of stories
- Top 3 headlines with their "why it matters" notes
- Delivery channel that will be used

**STEP 2 — Ask for feedback:**
Ask the user:
- Are they happy with this selection?
- Do they want to add/remove any topics?
- Do they want to regenerate with different criteria?

Use ask_user() to wait for their response.

**STEP 3 — Handle response:**

If the user approves (e.g., "looks good", "yes", "send it"):
- set_output("review_status", "approved")

If the user wants changes (e.g., "add more AI stories", "remove that one"):
- set_output("review_status", "revise")
- set_output("revision_feedback", "<description of what to change>")

If the user wants to cancel:
- set_output("review_status", "cancelled")

**Presentation format:**
```
📰 **Your Hacker News Briefing Preview**

📅 Date: 2026-03-08 (America/New_York)
📊 Stories: 10 top picks
📧 Delivery: markdown

**Top 3 Headlines:**

1. [Story Title] (342 pts, 127 comments)
   Why it matters: This matters because...

2. [Story Title] (256 pts, 89 comments)
   Why it matters: This matters because...

3. [Story Title] (198 pts, 45 comments)
   Why it matters: This matters because...

---
Does this look good? Reply with:
- "yes" to proceed with delivery
- "revise" with feedback to adjust the briefing
- "cancel" to abort
```
""",
    tools=[],
)

deliver_briefing_node = NodeSpec(
    id="deliver-briefing",
    name="Deliver Briefing",
    description="Deliver the final briefing via the configured channel(s).",
    node_type="event_loop",
    client_facing=True,
    input_keys=["briefing_config", "ranked_briefing", "review_status"],
    output_keys=["delivery_result"],
    system_prompt="""\
You are the delivery coordinator for a Hacker News Briefing agent.

Your task: Deliver the briefing via the user's configured channel(s).

**Delivery Channels:**

1. **markdown** (always available):
   - Create a formatted markdown file using save_data and append_data
   - Use serve_file_to_user to deliver it
   - This is the default and requires no credentials

2. **email** (requires credentials):
   - Use send_email if email credentials are configured
   - If not configured, inform the user and fall back to markdown

3. **slack** (requires credentials):
   - Use slack_send_message if Slack credentials are configured
   - If not configured, inform the user and fall back to markdown

4. **all**:
   - Attempt all channels, use markdown as fallback

**STEP 1 — Build the markdown report:**

CRITICAL: Build the file in multiple append_data calls to avoid token limits.

First, call save_data with the header:
```
save_data(filename="hn_briefing.md", data="# Hacker News Briefing\\n\\nDate: ...")
```

Then, for each story, call append_data:
```
append_data(filename="hn_briefing.md", data="\\n## 1. Story Title\\n\\n...")
```

**Markdown format:**
```markdown
# Hacker News Briefing

**Date:** 2026-03-08 (America/New_York)
**Stories:** 10 top picks

---

## 1. Story Title

**Points:** 342 | **Comments:** 127 | **Topic:** AI

**Summary:** One sentence summary.

**Why it matters:** This matters because...

**Links:**
- [Article](https://...)
- [Hacker News Discussion](https://news.ycombinator.com/item?id=...)

---

## 2. Story Title
...
```

**STEP 2 — Deliver:**

For markdown:
```
serve_file_to_user(filename="hn_briefing.md", label="Hacker News Briefing", open_in_browser=false)
```

For email (if configured and requested):
- Format the briefing as HTML email body
- Use send_email with subject "Your Hacker News Briefing - YYYY-MM-DD"

For Slack (if configured and requested):
- Format as a condensed Slack message
- Use slack_send_message

**STEP 3 — Report delivery status:**

Use set_output("delivery_result", <JSON string>):
```json
{
  "status": "success",
  "channels_used": ["markdown"],
  "file_path": "/path/to/hn_briefing.md",
  "delivered_at": "2026-03-08T10:45:00Z"
}
```

If delivery fails:
```json
{
  "status": "partial",
  "channels_used": ["markdown"],
  "failed_channels": ["email"],
  "error": "Email credentials not configured",
  "file_path": "/path/to/hn_briefing.md"
}
```

**Rules:**
- Always deliver via markdown at minimum
- If external channels fail, inform the user but don't fail the whole delivery
- Print the file path so user can find the briefing later
""",
    tools=["save_data", "append_data", "serve_file_to_user"],
)

__all__ = [
    "intake_preferences_node",
    "collect_hn_candidates_node",
    "rank_and_summarize_node",
    "review_briefing_node",
    "deliver_briefing_node",
]
