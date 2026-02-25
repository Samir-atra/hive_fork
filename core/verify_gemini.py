
import os
import sys
from dotenv import load_dotenv

def verify_gemini():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ GOOGLE_API_KEY is not set in .env")
        return False
    
    print(f"✅ Found GOOGLE_API_KEY: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        import litellm
        print("Testing Gemini connection via LiteLLM...")
        # Note: LiteLLM uses GEMINI_API_KEY or GOOGLE_API_KEY for gemini/ models
        response = litellm.completion(
            model="gemini/gemini-1.5-flash",
            messages=[{"role": "user", "content": "Ping"}],
            api_key=api_key
        )
        print(f"✅ Gemini Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Gemini Call failed: {e}")
        return False

if __name__ == "__main__":
    if not verify_gemini():
        sys.exit(1)
