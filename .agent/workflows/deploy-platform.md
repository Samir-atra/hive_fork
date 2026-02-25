---
description: Deploy the Hive Unified Web Platform locally and in production.
---

# Hive Unified Web Platform Deployment Guide

This guide outlines the steps to deploy the Unified Web Platform, bridging the Hive backend with the interactive frontend.

## 1. Prerequisites
- Docker (for production)
- Node.js & npm
- Python 3.10+
- Hive Core installed (with API dependencies: `fastapi`, `uvicorn`, `sse-starlette`)

## 2. Local Development Execution

### A. Start the Hive Backend API
Run the agent in "serve" mode. Replace `<agent_path>` with your exported agent directory.
```bash
python -m framework.cli serve <agent_path> --port 8000
```

### B. Start the Frontend
Navigate to the `platform/` directory and run the dev server.
```bash
cd platform
npm install
npm run dev
```
The platform will be available at `http://localhost:5173`.

## 3. Production Deployment (Unified)

### A. Build the Frontend
```bash
cd platform
npm run build
```
This generates the static assets in `platform/dist`.

### B. Serve via FastAPI (Production Mode)
You can configure the Hive API to serve the static frontend files as well for a single-binary deployment.

// turbo
#### Update server.py to serve static files (Optional)
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="platform/dist", html=True), name="static")
```

### C. Containerization
Use the provided `Dockerfile` (to be created) to bundle the backend and frontend into a single image.

```bash
docker build -t hive-platform .
docker run -p 8000:8000 hive-platform
```

## 4. Integration Verification
1. Access the dashboard at `http://localhost:8000`.
2. Go to **Goal Studio** and submit a goal.
3. Switch to **Live Generation View** to verify SSE events are streaming.
4. Check **Execution Cinema** for decision trails.
