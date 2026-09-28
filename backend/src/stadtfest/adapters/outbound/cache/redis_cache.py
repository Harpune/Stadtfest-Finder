"""Redis implementation of the cache port (public, non-personal data only)."""

from __future__ import annotations

import json

from redis.asyncio import Redis

from stadtfest.application.shared.ports import JsonValue


class RedisCache:
    """JSON cache with namespace generations for bulk invalidation."""

    def __init__(self, client: Redis, prefix: str = "sf:") -> None:
        """Create the adapter.

        Args:
            client: Redis client (decode_responses=True).
            prefix: Key prefix to separate this app's keys.
        """
        self._client = client
        self._prefix = prefix

    async def get_json(self, key: str) -> JsonValue | None:
        """Return the cached value or None."""
        raw = await self._client.get(self._prefix + key)
        if raw is None:
            return None
        value: JsonValue = json.loads(raw)
        return value

    async def set_json(self, key: str, value: JsonValue, ttl_seconds: int) -> None:
        """Store a value with a time-to-live."""
        await self._client.set(
            self._prefix + key, json.dumps(value, separators=(",", ":")), ex=ttl_seconds
        )

    async def generation(self, namespace: str) -> int:
        """Return the generation counter of a namespace."""
        raw = await self._client.get(f"{self._prefix}gen:{namespace}")
        return int(raw) if raw is not None else 0

    async def bump_generation(self, namespace: str) -> int:
        """Increment the generation counter."""
        return int(await self._client.incr(f"{self._prefix}gen:{namespace}"))
