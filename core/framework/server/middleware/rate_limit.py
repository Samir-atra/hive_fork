import time
from collections import defaultdict

from aiohttp import web


class RateLimiter:
    """Basic in-memory sliding window rate limiter per IP address."""

    def __init__(self) -> None:
        self.requests: dict[str, list[float]] = defaultdict(list)
        self._last_gc = time.time()

    def is_allowed(self, ip: str, max_requests: int, window: int) -> bool:
        now = time.time()

        # GC old IPs every 5 minutes to prevent memory leaks
        if now - self._last_gc > 300:
            empty_keys = [
                k for k, v in self.requests.items() if not [t for t in v if now - t < window]
            ]
            for k in empty_keys:
                del self.requests[k]
            self._last_gc = now

        # Clean up old requests for this IP
        self.requests[ip] = [t for t in self.requests[ip] if now - t < window]

        if len(self.requests[ip]) >= max_requests:
            return False

        self.requests[ip].append(now)
        return True

_rate_limiter = RateLimiter()

@web.middleware
async def rate_limit_middleware(request: web.Request, handler):
    """Rate limit requests per IP."""
    server_config = request.app.get("server_config")
    if not server_config:
        return await handler(request)

    # Skip if rate limiting is disabled
    if server_config.rate_limit_requests <= 0:
        return await handler(request)

    # Get client IP
    client_ip = request.headers.get("X-Forwarded-For", request.remote)
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = "unknown"

    if not _rate_limiter.is_allowed(
        client_ip, server_config.rate_limit_requests, server_config.rate_limit_window
    ):
        raise web.HTTPTooManyRequests(reason="Rate limit exceeded")

    return await handler(request)

    # Get client IP
    client_ip = request.headers.get("X-Forwarded-For", request.remote)
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = "unknown"

    if not _rate_limiter.is_allowed(
        client_ip, server_config.rate_limit_requests, server_config.rate_limit_window
    ):
        raise web.HTTPTooManyRequests(reason="Rate limit exceeded")

    return await handler(request)
