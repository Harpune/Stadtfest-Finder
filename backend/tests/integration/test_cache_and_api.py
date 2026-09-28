"""Redis cache adapter and the public API end-to-end (real PostGIS, Redis, seed)."""

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.application.events.use_cases import CATALOG_NAMESPACE, CATEGORIES_NAMESPACE
from stadtfest.bootstrap.app import create_app
from stadtfest.bootstrap.settings import Settings
from tests.integration.seed_support import listed, load, seed_id

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def seeded(integration_settings: Settings) -> None:
    engine = create_async_engine(str(integration_settings.database_url))
    await load(async_sessionmaker(engine), BerlinClock().today())
    await engine.dispose()
    # Earlier tests (e.g. contract tests) may have cached results for today: invalidate them.
    redis = Redis.from_url(str(integration_settings.redis_url), decode_responses=True)
    cache = RedisCache(redis)
    await cache.bump_generation(CATALOG_NAMESPACE)
    await cache.bump_generation(CATEGORIES_NAMESPACE)
    await redis.aclose()


async def test_redis_cache_roundtrip_and_generations(redis_url: str) -> None:
    client = Redis.from_url(redis_url, decode_responses=True)
    cache = RedisCache(client, prefix="test:")
    await cache.set_json("k", {"a": [1, "b", None]}, 60)
    assert await cache.get_json("k") == {"a": [1, "b", None]}
    assert await cache.get_json("missing") is None
    before = await cache.generation("ns")
    assert await cache.bump_generation("ns") == before + 1
    assert 0 < await client.ttl("test:k") <= 60
    await client.aclose()


@pytest.mark.usefixtures("seeded")
def test_public_api_end_to_end(integration_settings: Settings) -> None:
    today = BerlinClock().today()
    with TestClient(create_app(integration_settings)) as client:
        page = client.get("/v1/events", params={"limit": 500}).json()
        names = {item["name"] for item in page["items"]}
        assert names == {e.name for e in listed(today)}

        detail = client.get(f"/v1/events/{seed_id('event', 'reichsstaedter-tage')}")
        assert detail.status_code == 200
        assert detail.json()["program"]

        draft = client.get(f"/v1/events/{seed_id('event', 'oberkochener-lichterfest')}")
        assert draft.status_code == 404

        categories = client.get("/v1/categories")
        assert "Weinfest" not in {c["name"] for c in categories.json()}  # inactive
        assert (
            client.get(
                "/v1/categories", headers={"If-None-Match": categories.headers["etag"]}
            ).status_code
            == 304
        )

        count = client.get("/v1/events/count", params={"q": "Weihnachtsmarkt"}).json()
        assert count["total"] >= 1

        geo = client.get("/v1/geocode", params={"q": "73430"})  # fake geocoding in tests
        assert geo.json()[0]["postalCode"] == "73430"
