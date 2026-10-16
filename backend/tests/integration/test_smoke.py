"""Post-deployment smoke test (R16) against the real API and MCP apps (PostGIS, Redis, seed)."""

from collections.abc import AsyncIterator

import httpx
import pytest
from fastmcp.utilities.asgi_transport import run_asgi_lifespan
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.application.events.use_cases import CATALOG_NAMESPACE
from stadtfest.bootstrap.app import create_app
from stadtfest.bootstrap.mcp import create_mcp_app
from stadtfest.bootstrap.settings import Settings
from stadtfest.bootstrap.smoke import run_smoke_tests
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration


@pytest.fixture
async def clients(
    integration_settings: Settings,
) -> AsyncIterator[tuple[httpx.AsyncClient, httpx.AsyncClient]]:
    engine = create_async_engine(str(integration_settings.database_url))
    await load(async_sessionmaker(engine), BerlinClock().today())
    await engine.dispose()
    redis = Redis.from_url(str(integration_settings.redis_url), decode_responses=True)
    await RedisCache(redis).bump_generation(CATALOG_NAMESPACE)
    await redis.aclose()

    api_app = create_app(integration_settings)
    mcp_app = create_mcp_app(integration_settings)
    async with (
        run_asgi_lifespan(api_app),
        run_asgi_lifespan(mcp_app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api_app), base_url="http://api.test"
        ) as api,
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=mcp_app), base_url="http://mcp.test"
        ) as mcp,
    ):
        yield api, mcp


async def test_smoke_checks_pass_against_the_running_stack(
    clients: tuple[httpx.AsyncClient, httpx.AsyncClient],
) -> None:
    api, mcp = clients

    results = await run_smoke_tests(api, mcp)

    assert [(result.name, result.ok) for result in results] == [
        ("api health live", True),
        ("api health ready", True),
        ("GET /v1/categories", True),
        ("GET /v1/events", True),
        ("MCP search_events", True),
    ], [result.detail for result in results]
    assert results[-1].detail != "0 events"


async def test_smoke_checks_fail_without_a_reachable_stack() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(refuse)
    async with (
        httpx.AsyncClient(transport=transport, base_url="http://api.test") as api,
        httpx.AsyncClient(transport=transport, base_url="http://mcp.test") as mcp,
    ):
        results = await run_smoke_tests(api, mcp)

    assert not any(result.ok for result in results)
    assert {result.detail for result in results} == {"ConnectError"}
