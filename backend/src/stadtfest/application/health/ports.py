"""Outbound port for dependency probes."""

from __future__ import annotations

from typing import Protocol


class DependencyProbe(Protocol):
    """Checks whether a single external dependency is reachable."""

    @property
    def name(self) -> str:
        """Stable identifier of the dependency, e.g. `database`."""
        ...

    async def is_available(self) -> bool:
        """Return True if the dependency answers within its timeout."""
        ...
