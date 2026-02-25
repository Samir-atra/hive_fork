import asyncio
from framework.llm.litellm import LiteLLMProvider
from dotenv import load_dotenv

load_dotenv()

async def test():
    # Trying different model name format for Gemini in LiteLLM
    # LiteLLM usually expects "gemini/gemini-1.5-flash-latest" or similar
    provider = LiteLLMProvider(model="gemini/gemini-1.5-flash")
    print("Testing gemini/gemini-1.5-flash...")
    try:
        resp = await asyncio.to_thread(provider.complete, messages=[{"role": "user", "content": "Hello"}])
        print(f"Success! Content: {resp.content}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
