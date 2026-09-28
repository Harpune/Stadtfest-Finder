"""Fixed-window rate limiting per client in Redis. Client IPs are hashed and expire after 2 s."""

from __future__ import annotations

import hashlib
import time

from fastapi import HTTPException, Request
from redis.asyncio import Redis


class RateLimit:
    """FastAPI dependency allowing `limit` requests per second and client for a scope."""

    def __init__(self, scope: str, limit: int) -> None:
        """Create the limiter.

        Args:
            scope: Name of the limited endpoint group, e.g. `geocode`.
            limit: Allowed requests per second and client.
        """
        self._scope = scope
        self._limit = limit

    async def __call__(self, request: Request) -> None:
        """Raise 429 when the client exceeded the limit in the current second."""
        redis: Redis = request.app.state.container.redis
        client = request.client.host if request.client else "unknown"
        client_hash = hashlib.sha256(client.encode()).hexdigest()[:16]
        key = f"sf:ratelimit:{self._scope}:{client_hash}:{int(time.time())}"
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, 2)
        if count > self._limit:
            raise HTTPException(status_code=429, headers={"Retry-After": "1"})
