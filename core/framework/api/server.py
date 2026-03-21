"""FastAPI application server for the REST API layer."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from framework.api.middleware.error_handler import custom_exception_handler
from framework.api.middleware.logging import LoggingMiddleware
from framework.api.routes import agents, executions, tools

# Initialize FastAPI application
app = FastAPI(
    title="Hive REST API",
    description="Production-ready REST API layer for language-agnostic access to Hive.",
    version="1.0.0",
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handler
app.add_exception_handler(Exception, custom_exception_handler)

# Setup Logging middleware
app.add_middleware(LoggingMiddleware)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint for k8s/Docker and general monitoring.

    Returns:
        A dictionary indicating the API status.
    """
    return {"status": "ok"}


# Include routers
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(executions.router, tags=["Executions"])
app.include_router(tools.router, prefix="/tools", tags=["Tools"])
