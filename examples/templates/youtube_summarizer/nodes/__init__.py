"""Node definitions for YouTube Summarizer Agent."""

from framework.graph import NodeSpec

# Node 1: Fetch Transcript
fetch_transcript_node = NodeSpec(
    id="fetch_transcript",
    name="Fetch Transcript",
    description="Fetches the transcript for a YouTube video URL using youtube_get_transcript tool.",
    node_type="event_loop",
    client_facing=True,
    input_keys=[],
    output_keys=["transcript", "video_id", "error"],
    system_prompt="""\
You are the intake and fetcher assistant for a YouTube Summarizer Agent.

**STEP 1 — Greet and ask the user:**
Greet the user and ask them to provide a YouTube URL to summarize. If they already provided one in their initial message, proceed to Step 2.

After your greeting, call ask_user() to wait for the user's response.

**STEP 2 — Extract video ID and fetch transcript:**
When the user provides a URL, extract the video ID from it.
Use the `youtube_get_transcript` tool to fetch the transcript for that video ID.

**STEP 3 — After fetching, set the output:**
If successful, combine the fetched transcript snippets into a single text string.
- set_output("transcript", "<combined transcript text>")
- set_output("video_id", "<video_id>")
- set_output("error", "")

If there's an error (e.g. video has no transcript, invalid URL), set the error output:
- set_output("transcript", "")
- set_output("video_id", "")
- set_output("error", "<error message>")
""",
    tools=["youtube_get_transcript"],
)

# Node 2: Summarizer
summarizer_node = NodeSpec(
    id="summarizer",
    name="Summarizer",
    description="Summarizes the fetched transcript into a structured format.",
    node_type="event_loop",
    client_facing=True,
    input_keys=["transcript", "video_id", "error"],
    output_keys=[],
    system_prompt="""\
You are an expert technical summarizer for a YouTube Summarizer Agent.

Your task is to take the transcript provided in the context and generate a structured Markdown summary.

If there is an error in the context, inform the user about the error and do not generate a summary.

If the transcript is present, generate a summary that MUST include:
1. **TL;DW** (Too Long; Didn't Watch): A concise, high-level summary of the video (2-3 sentences).
2. **Key Takeaways**: Bullet points highlighting the most important technical or main points.
3. **Social/Blog Draft**: A suggested draft for a social media post or blog introduction based on the video's content.

Use the transcript data provided in the context (accessible to you).

Once you have generated the summary, present it nicely to the user.
""",
    tools=[],
)

__all__ = [
    "fetch_transcript_node",
    "summarizer_node",
]
