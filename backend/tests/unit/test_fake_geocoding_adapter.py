"""Tests for the fake geocoding adapter used in local development."""

from __future__ import annotations

import pytest

from stadtfest.adapters.outbound.geocoding.fake import FakeGeocoding
from stadtfest.application.geocoding.ports import PlaceKind
from stadtfest.domain.events.geo import GeoPoint


async def _labels(query: str, limit: int = 10) -> list[str]:
    return [place.label for place in await FakeGeocoding().search(query, limit)]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Marktplatz Aalen", "Marktplatz 1, 73430 Aalen"),
        ("aalen markt", "Marktplatz 1, 73430 Aalen"),
        ("Wasseralf", "Wasseralfingen"),
        ("Bahnhofstr Aalen", "Bahnhofstraße 1, 73430 Aalen"),
        ("schwabisch gmund", "Schwäbisch Gmünd"),
    ],
)
async def test_search_matches_word_prefixes_in_any_order(query: str, expected: str) -> None:
    assert expected in await _labels(query)


async def test_search_ranks_places_whose_label_starts_with_the_query_first() -> None:
    labels = await _labels("Aalen")

    assert labels[0].startswith("Aalen")


async def test_search_respects_the_limit() -> None:
    assert len(await _labels("Aalen", limit=2)) == 2


async def test_search_without_match_returns_nothing() -> None:
    assert await _labels("Hamburg") == []


async def test_reverse_returns_the_nearest_postcode() -> None:
    place = await FakeGeocoding().reverse(GeoPoint(48.8700, 10.1050))

    assert place is not None
    assert place.kind is PlaceKind.POSTCODE
    assert place.postal_code == "73433"
