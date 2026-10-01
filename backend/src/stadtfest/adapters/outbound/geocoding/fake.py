"""Fake geocoding with fixed places around Aalen (local development and tests only)."""

from __future__ import annotations

import re
import unicodedata

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
    Place("73432 Aalen", "Aalen", GeoPoint(48.8130, 10.1030), PlaceKind.POSTCODE, "73432"),
    Place("73433 Aalen", "Aalen", GeoPoint(48.8700, 10.1000), PlaceKind.POSTCODE, "73433"),
    Place("Wasseralfingen", "Aalen", GeoPoint(48.8667, 10.1000), PlaceKind.CITY, "73433"),
    Place("Unterkochen", "Aalen", GeoPoint(48.8160, 10.1290), PlaceKind.CITY, "73432"),
    Place(
        "Marktplatz 1, 73430 Aalen", "Aalen", GeoPoint(48.8368, 10.0932), PlaceKind.ADDRESS, "73430"
    ),
    Place(
        "Bahnhofstraße 1, 73430 Aalen",
        "Aalen",
        GeoPoint(48.8395, 10.0985),
        PlaceKind.ADDRESS,
        "73430",
    ),
    Place(
        "Gmünder Straße 9, 73430 Aalen",
        "Aalen",
        GeoPoint(48.8346, 10.0855),
        PlaceKind.ADDRESS,
        "73430",
    ),
    Place(
        "Stadtgarten, 73430 Aalen", "Aalen", GeoPoint(48.8380, 10.0870), PlaceKind.ADDRESS, "73430"
    ),
    Place(
        "Karlstraße 26, 73433 Aalen",
        "Aalen",
        GeoPoint(48.8655, 10.1005),
        PlaceKind.ADDRESS,
        "73433",
    ),
    Place(
        "Marktplatz 1, 73525 Schwäbisch Gmünd",
        "Schwäbisch Gmünd",
        GeoPoint(48.7996, 9.7986),
        PlaceKind.ADDRESS,
        "73525",
    ),
    Place(
        "Marktplatz 1, 73479 Ellwangen (Jagst)",
        "Ellwangen (Jagst)",
        GeoPoint(48.9614, 10.1306),
        PlaceKind.ADDRESS,
        "73479",
    ),
)

_UMLAUTS = str.maketrans({"ß": "ss"})


def _words(text: str) -> list[str]:
    """Lower-case words without accents, so "gmund" finds "Gmünd"."""
    folded = unicodedata.normalize("NFKD", text.lower().translate(_UMLAUTS))
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", plain)


def _matches(query_words: list[str], label: str) -> bool:
    """True if every query word starts a word of the label (any order), like typing ahead."""
    label_words = _words(label)
    return all(any(word.startswith(q) for word in label_words) for q in query_words)


class FakeGeocoding:
    """Deterministic `GeocodingPort` without network access."""

    async def search(self, query: str, limit: int) -> list[Place]:
        """Return fixed places whose words start with the query words, label prefix first."""
        query_words = _words(query)
        if not query_words:
            return []
        found = [place for place in _PLACES if _matches(query_words, place.label)]
        first = query_words[0]
        found.sort(key=lambda place: not _words(place.label)[0].startswith(first))
        return found[:limit]

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
