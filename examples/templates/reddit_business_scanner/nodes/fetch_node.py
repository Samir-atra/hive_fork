from framework.graph import NodeSpec

fetch_node = NodeSpec(
    id="fetch-reddit-posts",
    name="Fetch Reddit Posts",
    description="Fetch recent posts from targeted subreddits using Reddit tools.",
    node_type="event_loop",
    client_facing=False,
    max_node_visits=1,
    input_keys=["user_request", "target_subreddits"],
    output_keys=["raw_posts"],
    tools=["reddit_get_posts"],
    system_prompt="""\
You are an expert at extracting business value from Reddit.
Your task is to fetch the most recent and top posts from the targeted subreddits.

## Instructions
1. For each subreddit in `target_subreddits` (or default ones if none provided, e.g., SaaS, entrepreneur):
   - Call `reddit_get_posts` with the subreddit name.
2. Aggregate all the fetched posts into a single JSON array.
3. Save the fetched posts to context.

Example:
```python
set_output("raw_posts", aggregated_posts)
```
""",
)
