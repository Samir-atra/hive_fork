
import os
import sys
from dotenv import load_dotenv

def verify_anthropic():
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY is not set in .env")
        return False
    
    print(f"✅ Found ANTHROPIC_API_KEY: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        # Try a minimal message
        print("Testing API connection...")
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Ping"}]
        )
        print(f"✅ API Response: {message.content[0].text}")
        return True
    except Exception as e:
        print(f"❌ API Call failed: {e}")
        return False

if __name__ == "__main__":
    if not verify_anthropic():
        sys.exit(1)
