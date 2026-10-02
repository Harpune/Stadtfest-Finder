"""Geocoding use cases with caching (TTL 30 days, CLAUDE.md "Caching")."""

from __future__ import annotations

import hashlib
from typing import cast

from stadtfest.application.geocoding.ports import (
    GeocodingPort,
    GeocodingUnavailableError,
    Place,
    PlaceKind,
)
from stadtfest.application.shared.errors import (
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.application.shared.ports import CachePort, JsonValue
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal

GEOCODING_TTL_SECONDS = 30 * 24 * 60 * 60
REVERSE_GRID_DECIMALS = 3  # ~100 m; exact coordinates never reach the cache key
PIN_DECIMALS = 5  # ~1 m: event pins are public data, not user positions
UNAVAILABLE = "geocoding_unavailable"


def _place_to_json(place: Place) -> dict[str, JsonValue]:
    return {
        "label": place.label,
        "city": place.city,
        "lat": place.location.lat,
        "lon": place.location.lon,
        "kind": place.kind.value,
        "postalCode": place.postal_code,
        "street": place.street,
    }


def _place_from_json(value: dict[str, JsonValue]) -> Place:
    postal_code = value.get("postalCode")
    return Place(
        label=str(value["label"]),
        city=str(value["city"]),
        location=GeoPoint(float(cast("float", value["lat"])), float(cast("float", value["lon"]))),
        kind=PlaceKind(str(value["kind"])),
        postal_code=str(postal_code) if postal_code is not None else None,
        street=str(value["street"]) if value.get("street") else None,
    )


def _normalize(query: str) -> str:
    return " ".join(query.lower().split())


class Geocode:
    """Suggest places for a search text."""

    def __init__(self, geocoding: GeocodingPort, cache: CachePort) -> None:
        """Create the use case."""
        self._geocoding = geocoding
        self._cache = cache

    async def __call__(self, query: str, limit: int = 5) -> list[Place]:
        """Return suggestions.

        Raises:
            ServiceUnavailableError: If the geocoding service is down.
        """
        normalized = _normalize(query)
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        key = f"geocode:search:{digest}:{limit}"
        cached = await self._cache.get_json(key)
        if isinstance(cached, list):
            return [_place_from_json(cast("dict[str, JsonValue]", item)) for item in cached]
        try:
            places = await self._geocoding.search(normalized, limit)
        except GeocodingUnavailableError:
            raise ServiceUnavailableError(UNAVAILABLE) from None
        await self._cache.set_json(
            key, [_place_to_json(place) for place in places], GEOCODING_TTL_SECONDS
        )
        return places


class ReverseGeocode:
    """Resolve coordinates to a place."""

    def __init__(self, geocoding: GeocodingPort, cache: CachePort) -> None:
        """Create the use case."""
        self._geocoding = geocoding
        self._cache = cache

    async def __call__(self, location: GeoPoint) -> Place:
        """Return the place.

        The coordinate is rounded to a ~100 m grid before lookup and caching, so exact user
        positions are neither sent in full precision nor stored.

        Raises:
            NotFoundError: If no place is found (e.g. outside Germany).
            ServiceUnavailableError: If the geocoding service is down.
        """
        grid = location.rounded(REVERSE_GRID_DECIMALS)
        key = f"geocode:reverse:{grid.lat:.3f}:{grid.lon:.3f}"
        cached = await self._cache.get_json(key)
        if isinstance(cached, dict):
            return _place_from_json(cached)
        try:
            place = await self._geocoding.reverse(grid)
        except GeocodingUnavailableError:
            raise ServiceUnavailableError(UNAVAILABLE) from None
        if place is None:
            raise NotFoundError("no place at location")
        await self._cache.set_json(key, _place_to_json(place), GEOCODING_TTL_SECONDS)
        return place


class ReverseGeocodeEventLocation:
    """Address of an event pin for moderators (street, ZIP code, place).

    Unlike `ReverseGeocode` the pin is used in full precision (rounded to ~1 m): an event
    location is public data, not a user position.
    """

    def __init__(self, geocoding: GeocodingPort, cache: CachePort) -> None:
        """Create the use case."""
        self._geocoding = geocoding
        self._cache = cache

    async def __call__(self, principal: Principal, location: GeoPoint) -> Place:
        """Return the place at the pin.

        Raises:
            ForbiddenError: If the caller is no moderator.
            NotFoundError: If no place is found (e.g. outside Germany).
            ServiceUnavailableError: If the geocoding service is down.
        """
        if not principal.can_moderate:
            raise ForbiddenError
        pin = location.rounded(PIN_DECIMALS)
        key = f"geocode:pin:{pin.lat:.5f}:{pin.lon:.5f}"
        cached = await self._cache.get_json(key)
        if isinstance(cached, dict):
            return _place_from_json(cached)
        try:
            place = await self._geocoding.reverse(pin)
        except GeocodingUnavailableError:
            raise ServiceUnavailableError(UNAVAILABLE) from None
        if place is None:
            raise NotFoundError("no place at location")
        await self._cache.set_json(key, _place_to_json(place), GEOCODING_TTL_SECONDS)
        return place
