"""Cross-cutting outbound ports: clock and cache."""

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
