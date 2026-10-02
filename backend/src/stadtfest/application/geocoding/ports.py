"""Outbound port for geocoding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from stadtfest.domain.events.geo import GeoPoint


class PlaceKind(StrEnum):
    """Kind of a geocoding result."""

    POSTCODE = "postcode"
    CITY = "city"
    ADDRESS = "address"


@dataclass(frozen=True, slots=True)
class Place:
    """A geocoded place in Germany."""

    label: str
    city: str
    location: GeoPoint
    kind: PlaceKind
    postal_code: str | None = None
    # Street and house number; only reverse lookups of event pins fill it (R07-US3).
    street: str | None = None


class GeocodingUnavailableError(Exception):
    """Raised by adapters when the geocoding service cannot be reached."""


class GeocodingPort(Protocol):
    """Forward and reverse geocoding (Germany only)."""

    async def search(self, query: str, limit: int) -> list[Place]:
        """Return places matching a city, ZIP code or address, best match first.

        Raises:
            GeocodingUnavailableError: If the service is unavailable.
        """
        ...

    async def reverse(self, location: GeoPoint) -> Place | None:
        """Return the place at a coordinate, or None if nothing is found.

        Raises:
            GeocodingUnavailableError: If the service is unavailable.
        """
        ...
