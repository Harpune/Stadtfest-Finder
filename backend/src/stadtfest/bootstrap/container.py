"""Composition root: creates infrastructure resources and wires ports to adapters."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.cache.redis_client import RedisProbe, create_redis
from stadtfest.adapters.outbound.clock.berlin_clock import BerlinClock
from stadtfest.adapters.outbound.geocoding.fake import FakeGeocoding
from stadtfest.adapters.outbound.geocoding.nominatim import (
    NominatimGeocoding,
    create_nominatim_client,
)
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.database import DatabaseProbe, create_engine
from stadtfest.application.events.use_cases import (
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.geocoding.ports import GeocodingPort
from stadtfest.application.geocoding.use_cases import Geocode, ReverseGeocode
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.bootstrap.settings import GeocodingProvider, Settings


@dataclass
class Container:
    """Process-wide dependencies shared by the API, the worker and the MCP server."""

    settings: Settings
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]
    redis: Redis
    http: httpx.AsyncClient | None
    check_readiness: CheckReadiness
    search_events: SearchEvents
    count_events: CountEvents
    get_public_event: GetPublicEvent
    list_active_categories: ListActiveCategories
    geocode: Geocode
    reverse_geocode: ReverseGeocode

    @classmethod
    def build(cls, settings: Settings) -> Container:
        """Create all resources and use cases for the given settings.

        Args:
            settings: Validated application settings.

        Returns:
            The wired container. Call `aclose()` on shutdown.
        """
        engine = create_engine(str(settings.database_url))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        redis = create_redis(str(settings.redis_url))
        cache = RedisCache(redis)
        clock = BerlinClock()
        catalog = SqlCatalog(sessions)

        http: httpx.AsyncClient | None = None
        geocoding: GeocodingPort
        if settings.geocoding_provider is GeocodingProvider.NOMINATIM:
            http = create_nominatim_client(
                str(settings.nominatim_url), settings.geocoding_timeout_seconds
            )
            geocoding = NominatimGeocoding(http)
        else:
            geocoding = FakeGeocoding()

        return cls(
            settings=settings,
            engine=engine,
            sessions=sessions,
            redis=redis,
            http=http,
            check_readiness=CheckReadiness([DatabaseProbe(engine), RedisProbe(redis)]),
            search_events=SearchEvents(catalog, cache, clock),
            count_events=CountEvents(catalog, cache, clock),
            get_public_event=GetPublicEvent(catalog),
            list_active_categories=ListActiveCategories(catalog, cache),
            geocode=Geocode(geocoding, cache),
            reverse_geocode=ReverseGeocode(geocoding, cache),
        )

    async def aclose(self) -> None:
        """Release all resources."""
        if self.http is not None:
            await self.http.aclose()
        await self.redis.aclose()
        await self.engine.dispose()
