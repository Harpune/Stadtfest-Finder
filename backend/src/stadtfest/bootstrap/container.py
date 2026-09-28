"""Composition root: creates infrastructure resources and wires ports to adapters."""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from stadtfest.adapters.outbound.cache.redis_client import RedisProbe, create_redis
from stadtfest.adapters.outbound.persistence.database import DatabaseProbe, create_engine
from stadtfest.application.health.check_readiness import CheckReadiness
from stadtfest.bootstrap.settings import Settings


@dataclass
class Container:
    """Process-wide dependencies shared by the API, the worker and the MCP server."""

    settings: Settings
    engine: AsyncEngine
    redis: Redis
    check_readiness: CheckReadiness

    @classmethod
    def build(cls, settings: Settings) -> Container:
        """Create all resources and use cases for the given settings.

        Args:
            settings: Validated application settings.

        Returns:
            The wired container. Call `aclose()` on shutdown.
        """
        engine = create_engine(str(settings.database_url))
        redis = create_redis(str(settings.redis_url))
        return cls(
            settings=settings,
            engine=engine,
            redis=redis,
            check_readiness=CheckReadiness([DatabaseProbe(engine), RedisProbe(redis)]),
        )

    async def aclose(self) -> None:
        """Release all resources."""
        await self.redis.aclose()
        await self.engine.dispose()
