"""Redis client factory and a readiness probe for Redis."""

from __future__ import annotations

from redis.asyncio import Redis


def create_redis(redis_url: str) -> Redis:
    """Create the process-wide Redis client.

    Args:
        redis_url: Redis connection URL.

    Returns:
        The client; close it on shutdown.
    """
    client: Redis = Redis.from_url(redis_url, decode_responses=True)
    return client


class RedisProbe:
    """Readiness probe that sends PING to Redis."""

    name = "redis"

    def __init__(self, client: Redis) -> None:
        """Create the probe.

        Args:
            client: Client to check.
        """
        self._client = client

    async def is_available(self) -> bool:
        """Return True if Redis answers PING."""
        return bool(await self._client.ping())
