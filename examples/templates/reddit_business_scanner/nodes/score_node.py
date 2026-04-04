from framework.graph import NodeSpec

score_node = NodeSpec(
    id="score-opportunities",
    name="Score Business Opportunities",
    description="Filter posts using keywords and score them for business signal. Enriches with web scraping if URLs exist.",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["raw_posts"],
    output_keys=["scored_leads"],
    tools=["web_scrape_tool", "exa_search"],
    system_prompt="""\
You are an expert lead qualification agent.
Your task is to analyze raw Reddit posts, score them for business potential, and filter out low-value posts.

## Instructions
1. For each post in `raw_posts`:
   - Check if it contains keywords like "looking for", "frustrated with", "does anyone know", "pain point", "alternative".
   - If it matches, score the post (0-10) based on:
     - Problem severity
     - Audience size
     - Urgency
     - Fit for a product/service solution
   - If the score >= 7:
     - If the post contains a URL, try to use `web_scrape_tool` to enrich context.
     - Keep the lead.
2. Compile a list of valid leads (score >= 7). Each lead should have:
   - `subreddit`: The subreddit it came from
   - `title`: Post title
   - `url`: Post URL
   - `score`: Your assigned score
   - `reasoning`: A short explanation of why it scored high
   - `content`: Relevant post text
   - `enriched_data`: (Optional) data from scraping
3. Save the leads list.

Example:
```python
set_output("scored_leads", valid_leads)
```
""",
)
