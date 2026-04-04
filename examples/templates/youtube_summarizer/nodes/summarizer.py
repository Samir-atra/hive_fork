from typing import Any, Dict

from framework.graph.node import NodeSpec
from framework.llm.provider import LLMProvider

async def summarize_transcript(context: Dict[str, Any], llm_provider: LLMProvider) -> Dict[str, Any]:
    """
    Summarizes the fetched transcript into a structured Markdown format.
    """
    transcript = context.get("transcript", "")
    error = context.get("error")

    if error:
        return {"summary": f"**Error fetching transcript:** {error}"}

    if not transcript:
        return {"summary": "**Error:** No transcript available to summarize."}

    prompt = f"""
    You are an expert technical summarizer. Please read the following YouTube video transcript and generate a structured Markdown summary.

    The summary MUST include:
    1. **TL;DW** (Too Long; Didn't Watch): A concise, high-level summary of the video (2-3 sentences).
    2. **Key Takeaways**: Bullet points highlighting the most important technical or main points.
    3. **Social/Blog Draft**: A suggested draft for a social media post or blog introduction based on the video's content.

    Transcript:
    ---
    {transcript}
    ---

    Please provide the structured summary below:
    """

    # We use a default model if not provided in config
    model = context.get("model", "gpt-4o")
    temperature = context.get("temperature", 0.7)

    try:
        response = await llm_provider.generate(
            prompt=prompt,
            model=model,
            temperature=temperature
        )
        return {"summary": response.content}
    except Exception as e:
        return {"summary": f"**Error generating summary:** {str(e)}"}

summarizer_node = NodeSpec(
    name="summarizer",
    description="Summarizes the YouTube transcript into a structured format.",
    input_keys=["transcript", "error", "model", "temperature"],
    output_keys=["summary"],
    handler=summarize_transcript,
)
