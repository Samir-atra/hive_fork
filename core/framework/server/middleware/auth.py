import hmac

from aiohttp import web


@web.middleware
async def api_key_auth_middleware(request: web.Request, handler):
    """Require API key for all routes except OPTIONS, health check, and static files."""
    if request.method == "OPTIONS":
        return await handler(request)

    if request.path == "/api/health":
        return await handler(request)

    # Allow static frontend routes to bypass auth
    if not request.path.startswith("/api/"):
        return await handler(request)

    server_config = request.app.get("server_config")
    if not server_config:
        return await handler(request)

    # Backward compatibility: if no API key is configured, allow all
    if not server_config.api_key:
        return await handler(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Missing or invalid Authorization header")

    token = auth_header[7:]
    if not hmac.compare_digest(token, server_config.api_key):
        raise web.HTTPUnauthorized(reason="Invalid API key")

    return await handler(request)
