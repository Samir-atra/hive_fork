import sys
import os

# Add core to sys.path
sys.path.append(os.path.join(os.getcwd(), "core"))

print("Importing server...")
try:
    from core import server
    print("Server imported successfully.")
except ImportError as e:
    print(f"Failed to import server: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during import: {e}")
    sys.exit(1)

print("Checking dependencies...")
try:
    import litellm
    print("litellm imported.")
    import fastapi
    print("fastapi imported.")
    import uvicorn
    print("uvicorn imported.")
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

print("Test complete.")
