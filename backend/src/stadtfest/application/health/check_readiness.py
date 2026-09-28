"""Use case: determine whether the service is ready to serve traffic."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

from stadtfest.application.health.ports import DependencyProbe


@dataclass(frozen=True)
class Readiness:
    """Aggregated readiness result."""

    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        """Whether every dependency is available."""
        return all(self.checks.values())


class CheckReadiness:
    """Probe all dependencies concurrently; a failing probe marks the service unready."""

    def __init__(self, probes: Sequence[DependencyProbe], timeout_seconds: float = 2.0) -> None:
        """Create the use case.

        Args:
            probes: Dependencies to check.
            timeout_seconds: Maximum time per probe before it counts as unavailable.
        """
        self._probes = tuple(probes)
        self._timeout = timeout_seconds

    async def __call__(self) -> Readiness:
        """Run all probes.

        Returns:
            The readiness per dependency.
        """
        results = await asyncio.gather(*(self._probe(probe) for probe in self._probes))
        return Readiness(checks=dict(results))

    async def _probe(self, probe: DependencyProbe) -> tuple[str, bool]:
        try:
            available = await asyncio.wait_for(probe.is_available(), self._timeout)
        except Exception:  # noqa: BLE001  # any failure means "unavailable"
            available = False
        return probe.name, available
