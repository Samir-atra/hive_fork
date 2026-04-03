pytest_plugins = ["aiohttp.pytest_plugin"]

import pytest
from aiohttp import web

from framework.config import ServerConfig
from framework.server.middleware.auth import api_key_auth_middleware
from framework.server.middleware.rate_limit import rate_limit_middleware


@pytest.fixture
def mock_server_config():
    """Mock the server config for testing."""
    return ServerConfig(
        api_key="test-api-key",
        rate_limit_requests=2,
        rate_limit_window=1,
        cors_origins=["http://localhost"]
    )

async def test_auth_middleware_valid_key(mock_server_config, aiohttp_client):
    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[api_key_auth_middleware])
    app["server_config"] = mock_server_config
    app.router.add_get("/api/test", handler)

    client = await aiohttp_client(app)
    resp = await client.get("/api/test", headers={"Authorization": "Bearer test-api-key"})
    assert resp.status == 200
    assert await resp.text() == "OK"

async def test_auth_middleware_invalid_key(mock_server_config, aiohttp_client):
    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[api_key_auth_middleware])
    app["server_config"] = mock_server_config
    app.router.add_get("/api/test", handler)

    client = await aiohttp_client(app)
    resp = await client.get("/api/test", headers={"Authorization": "Bearer wrong-key"})
    assert resp.status == 401

async def test_auth_middleware_no_key_provided(mock_server_config, aiohttp_client):
    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[api_key_auth_middleware])
    app["server_config"] = mock_server_config
    app.router.add_get("/api/test", handler)

    client = await aiohttp_client(app)
    resp = await client.get("/api/test")
    assert resp.status == 401

async def test_auth_middleware_health_bypass(mock_server_config, aiohttp_client):
    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[api_key_auth_middleware])
    app["server_config"] = mock_server_config
    app.router.add_get("/api/health", handler)

    client = await aiohttp_client(app)
    resp = await client.get("/api/health")
    assert resp.status == 200

async def test_auth_middleware_no_config_bypass(aiohttp_client):
    config = ServerConfig(api_key=None)

    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[api_key_auth_middleware])
    app["server_config"] = config
    app.router.add_get("/api/test", handler)

    client = await aiohttp_client(app)
    resp = await client.get("/api/test")
    assert resp.status == 200

async def test_rate_limit_middleware(mock_server_config, aiohttp_client):
    async def handler(request):
        return web.Response(text="OK")

    app = web.Application(middlewares=[rate_limit_middleware])
    app["server_config"] = mock_server_config
    app.router.add_get("/api/test", handler)

    client = await aiohttp_client(app)

    # First request
    resp1 = await client.get("/api/test", headers={"X-Forwarded-For": "1.2.3.4"})
    assert resp1.status == 200

    # Second request
    resp2 = await client.get("/api/test", headers={"X-Forwarded-For": "1.2.3.4"})
    assert resp2.status == 200

    # Third request (should be rate limited)
    resp3 = await client.get("/api/test", headers={"X-Forwarded-For": "1.2.3.4"})
    assert resp3.status == 429

    # Request from different IP should work
    resp4 = await client.get("/api/test", headers={"X-Forwarded-For": "5.6.7.8"})
    assert resp4.status == 200
