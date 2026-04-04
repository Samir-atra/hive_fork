# YouTube Summarizer Agent

An agent that automatically produces a structured Markdown summary of a YouTube video based on its transcript.

## What it does

1.  **Fetcher**: Extracts the video ID from a given YouTube URL and uses the `youtube_transcript_tool` to pull the raw transcript text.
2.  **Summarizer**: Uses an LLM to transform the raw transcript into a structured Markdown format that includes:
    *   **TL;DW**: A concise, high-level summary of the video.
    *   **Key Takeaways**: Bullet points highlighting the most important technical or main points.
    *   **Social/Blog Draft**: A suggested draft for a social media post or blog introduction based on the video's content.

## Prerequisites

-   A YouTube URL.
-   The video must have captions/transcripts available.
-   `youtube-transcript-api` package installed.

## How to run

```bash
# Run the agent directly
uv run python -m examples.templates.youtube_summarizer --input '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```
