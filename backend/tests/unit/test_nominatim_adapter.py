"""Nominatim adapter against recorded responses (never the live service)."""

import json
from pathlib import Path

import httpx
import pytest

from stadtfest.adapters.outbound.geocoding.nominatim import NominatimGeocoding
from stadtfest.application.geocoding.ports import GeocodingUnavailableError, PlaceKind
from stadtfest.domain.events.geo import GeoPoint

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "nominatim"


def _adapter(handler: httpx.MockTransport) -> NominatimGeocoding:
    return NominatimGeocoding(
        httpx.AsyncClient(base_url="http://nominatim.test", transport=handler)
    )


def _fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


async def test_postcode_search_uses_structured_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_fixture("search_postcode_73430.json"))

    places = await _adapter(httpx.MockTransport(handler)).search("73430", 5)

    assert seen[0].url.params["postalcode"] == "73430"
    assert seen[0].url.params["country"] == "de"
    assert "q" not in seen[0].url.params
    assert places[0].label == "73430 Aalen"
    assert places[0].kind is PlaceKind.POSTCODE
    assert places[0].location == GeoPoint(48.8374832, 10.0933247)


async def test_free_text_search_maps_city_and_address() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["countrycodes"] == "de"
        return httpx.Response(200, json=_fixture("search_city_aalen.json"))

    city, address = await _adapter(httpx.MockTransport(handler)).search("aalen", 5)

    assert (city.kind, city.label, city.city) == (PlaceKind.CITY, "Aalen", "Aalen")
    assert (address.kind, address.label) == (PlaceKind.ADDRESS, "Marktplatz 1, 73430 Aalen")
    assert address.postal_code == "73430"


async def test_reverse_returns_postcode_place() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json=_fixture("reverse_aalen.json"))
    )
    place = await _adapter(transport).reverse(GeoPoint(48.837, 10.093))
    assert place is not None
    assert (place.label, place.postal_code, place.kind) == (
        "73430 Aalen",
        "73430",
        PlaceKind.POSTCODE,
    )


async def test_reverse_outside_germany_or_error_is_none() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"error": "Unable to geocode"})
    )
    assert await _adapter(transport).reverse(GeoPoint(0, 0)) is None


@pytest.mark.parametrize("status", [500, 503])
async def test_server_errors_mean_unavailable(status: int) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(status))
    with pytest.raises(GeocodingUnavailableError):
        await _adapter(transport).search("Aalen", 5)


async def test_network_errors_mean_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(GeocodingUnavailableError):
        await _adapter(httpx.MockTransport(handler)).search("Aalen", 5)
