"""MCP server end-to-end over the composition root (real PostGIS, Redis, seed), R15."""

from collections.abc import AsyncIterator

import pytest
from fastmcp.utilities.asgi_transport import run_asgi_lifespan
from fastmcp.utilities.tests import ASGIServer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.application.events.use_cases import CATALOG_NAMESPACE
from stadtfest.bootstrap.mcp import create_mcp_app
from stadtfest.bootstrap.settings import Settings
from tests.integration.seed_support import load, seed_id

pytestmark = pytest.mark.integration


@pytest.fixture
async def server(integration_settings: Settings) -> AsyncIterator[ASGIServer]:
    engine = create_async_engine(str(integration_settings.database_url))
    await load(async_sessionmaker(engine), BerlinClock().today())
    await engine.dispose()
    redis = Redis.from_url(str(integration_settings.redis_url), decode_responses=True)
    await RedisCache(redis).bump_generation(CATALOG_NAMESPACE)
    await redis.aclose()

    app = create_mcp_app(integration_settings)
    async with run_asgi_lifespan(app):
        yield ASGIServer(url="http://127.0.0.1/mcp", app=app, transport_type="http")


async def test_guest_search_and_detail_with_the_real_stack(server: ASGIServer) -> None:
    async with server.client() as client:
        found = await client.call_tool("search_events", {"zip_code": "73430", "radius_km": 50})
        assert found.structured_content is not None
        events = found.structured_content["events"]
        assert isinstance(events, list)
        reichsstaedter = str(seed_id("event", "reichsstaedter-tage"))
        assert reichsstaedter in {event["id"] for event in events}

        detail = await client.call_tool("get_event", {"event_id": reichsstaedter})
        assert detail.structured_content is not None
        assert detail.structured_content["program"]

    async with server.http_client() as http:
        assert (await http.get("/health/ready")).json()["status"] == "ok"
