"""Logging middleware for incoming requests."""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs the processing time and details of incoming requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log incoming request start and end times, including elapsed time."""
        start_time = time.perf_counter()

        # Log request start (optional, disabled to avoid log spam)
        # logger.debug("Request started: %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "Request failed: %s %s with error %s", request.method, request.url.path, exc
            )
            raise

        process_time = time.perf_counter() - start_time
        logger.info(
            "Request: %s %s - Status: %s - Time: %.4fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        return response
