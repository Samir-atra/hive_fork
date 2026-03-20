import subprocess
import time
import os

# Start the frontend and backend servers
backend_process = subprocess.Popen(["uv", "run", "python", "-m", "framework.cli", "run", "--model", "claude-haiku-4-5-20251001", "--dev"], cwd="core")
# Wait for backend to be ready
time.sleep(10)

frontend_process = subprocess.Popen(["npm", "run", "frontend:dev"], cwd=".")
# Wait for frontend to be ready
time.sleep(15)

print("Servers started")
