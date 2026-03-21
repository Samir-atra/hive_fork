"""Global exception handler for the FastAPI application."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handles unexpected exceptions and returns a structured JSON response."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "message": str(exc)},
    )
