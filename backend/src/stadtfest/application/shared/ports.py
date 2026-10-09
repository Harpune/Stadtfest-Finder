"""Cross-cutting outbound ports: clock, cache and rate limits."""

from __future__ import annotations

from datetime import date
from typing import Protocol

type JsonValue = bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None


class Clock(Protocol):
    """Provides the current day in Europe/Berlin (injectable for tests)."""

    def today(self) -> date:
        """Return the current day in Europe/Berlin."""
        ...


class CachePort(Protocol):
    """Key-value cache for public, non-personal data only (CLAUDE.md "Caching")."""

    async def get_json(self, key: str) -> JsonValue | None:
        """Return the cached value or None."""
        ...

    async def set_json(self, key: str, value: JsonValue, ttl_seconds: int) -> None:
        """Store a value with a time-to-live."""
        ...

    async def generation(self, namespace: str) -> int:
        """Return the current generation counter of a namespace (0 if unset)."""
        ...

    async def bump_generation(self, namespace: str) -> int:
        """Increment a namespace generation, invalidating all keys built with the old one."""
        ...


class RateLimiter(Protocol):
    """Counts attempts per key in a fixed window (Redis); keys hold no personal data."""

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Count one attempt; False if the limit of the current window is exceeded."""
        ...
