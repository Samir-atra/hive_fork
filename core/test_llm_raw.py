import asyncio
from framework.llm.litellm import LiteLLMProvider
from dotenv import load_dotenv

load_dotenv()

async def test():
    provider = LiteLLMProvider(model="gemini/gemini-1.5-flash")
    resp = await asyncio.to_thread(provider.complete, messages=[{"role": "user", "content": "Hello, write a 1 line python print statement."}])
    print(f"Model: {resp.model}")
    print(f"Content: {resp.content}")

if __name__ == "__main__":
    asyncio.run(test())
