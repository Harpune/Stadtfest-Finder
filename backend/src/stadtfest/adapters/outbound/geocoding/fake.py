"""Fake geocoding with fixed places around Aalen (local development and tests only)."""

from __future__ import annotations

from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.domain.events.geo import GeoPoint

_PLACES = (
    Place("73430 Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.POSTCODE, "73430"),
    Place("73431 Aalen", "Aalen", GeoPoint(48.8480, 10.0710), PlaceKind.POSTCODE, "73431"),
    Place("Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.CITY, "73430"),
    Place(
        "73525 Schwäbisch Gmünd",
        "Schwäbisch Gmünd",
        GeoPoint(48.7999, 9.7980),
        PlaceKind.POSTCODE,
        "73525",
    ),
    Place(
        "Schwäbisch Gmünd", "Schwäbisch Gmünd", GeoPoint(48.7999, 9.7980), PlaceKind.CITY, "73525"
    ),
    Place(
        "89518 Heidenheim an der Brenz",
        "Heidenheim an der Brenz",
        GeoPoint(48.6767, 10.1541),
        PlaceKind.POSTCODE,
        "89518",
    ),
    Place(
        "73479 Ellwangen (Jagst)",
        "Ellwangen (Jagst)",
        GeoPoint(48.9617, 10.1310),
        PlaceKind.POSTCODE,
        "73479",
    ),
    Place("89073 Ulm", "Ulm", GeoPoint(48.3984, 9.9916), PlaceKind.POSTCODE, "89073"),
    Place(
        "Marktplatz 1, 73430 Aalen", "Aalen", GeoPoint(48.8368, 10.0932), PlaceKind.ADDRESS, "73430"
    ),
)


class FakeGeocoding:
    """Deterministic `GeocodingPort` without network access."""

    async def search(self, query: str, limit: int) -> list[Place]:
        """Return fixed places whose label contains the query."""
        needle = query.strip().lower()
        return [place for place in _PLACES if needle in place.label.lower()][:limit]

    async def reverse(self, location: GeoPoint) -> Place | None:
        """Return the nearest fixed postcode place within ~30 km."""
        candidates = [place for place in _PLACES if place.kind is PlaceKind.POSTCODE]
        nearest = min(
            candidates,
            key=lambda p: (
                (p.location.lat - location.lat) ** 2 + (p.location.lon - location.lon) ** 2
            ),
        )
        distance_sq = (nearest.location.lat - location.lat) ** 2 + (
            nearest.location.lon - location.lon
        ) ** 2
        return nearest if distance_sq < 0.3**2 else None
