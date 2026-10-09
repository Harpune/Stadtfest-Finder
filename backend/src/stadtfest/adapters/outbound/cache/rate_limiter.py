"""Fixed-window rate limits in Redis (`RateLimiter` port)."""

from __future__ import annotations

import hashlib
import time

from redis.asyncio import Redis


class RedisRateLimiter:
    """Counts attempts per key and window; keys are hashed, counters expire with the window."""

    def __init__(self, redis: Redis) -> None:
        """Create the limiter."""
        self._redis = redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Count one attempt; False once more than `limit` happened in the window."""
        window = int(time.time()) // window_seconds
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        redis_key = f"sf:limit:{digest}:{window}"
        count = int(await self._redis.incr(redis_key))
        if count == 1:
            await self._redis.expire(redis_key, window_seconds)
        return count <= limit
