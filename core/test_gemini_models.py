import asyncio
from framework.llm.litellm import LiteLLMProvider
from dotenv import load_dotenv
import litellm

load_dotenv()

async def test_model(model_id):
    print(f"Testing {model_id}...")
    provider = LiteLLMProvider(model=model_id)
    try:
        # litellm._turn_on_debug()
        resp = await asyncio.to_thread(provider.complete, messages=[{"role": "user", "content": "1+1"}])
        print(f"  SUCCESS: {resp.content}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

async def main():
    models = ["gemini/gemini-2.5-flash", "gemini/gemini-2.0-flash", "gemini/gemini-2.0-flash-exp"]
    for m in models:
        if await test_model(m):
            print(f"\nRecommended model: {m}")
            # break

if __name__ == "__main__":
    asyncio.run(main())
