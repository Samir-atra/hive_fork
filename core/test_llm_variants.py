import asyncio
import litellm
from framework.llm.litellm import LiteLLMProvider
from dotenv import load_dotenv

load_dotenv()

async def test():
    variants = ["gemini/gemini-1.5-flash-latest", "gemini/gemini-1.5-flash", "google/gemini-1.5-flash"]
    for v in variants:
        print(f"Testing {v}...")
        provider = LiteLLMProvider(model=v)
        try:
            resp = await asyncio.to_thread(provider.complete, messages=[{"role": "user", "content": "1+1"}])
            print(f"  SUCCESS: {resp.content}")
            return
        except Exception as e:
            print(f"  FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test())
