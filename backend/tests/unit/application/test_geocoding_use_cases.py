import pytest

from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.geocoding.use_cases import Geocode, ReverseGeocode
from stadtfest.application.shared.errors import NotFoundError, ServiceUnavailableError
from stadtfest.domain.events.geo import GeoPoint
from tests.fakes import FakeCache, FakeGeocoding

AALEN = Place("73430 Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.POSTCODE, "73430")


async def test_geocode_normalizes_and_caches_for_30_days() -> None:
    geocoding = FakeGeocoding(places=[AALEN])
    cache = FakeCache()
    use_case = Geocode(geocoding, cache)

    assert await use_case("  AALEN ") == [AALEN]
    assert await use_case("aalen") == [AALEN]
    assert geocoding.search_calls == ["aalen"]
    assert set(cache.ttls.values()) == {30 * 24 * 60 * 60}


async def test_geocode_unavailable() -> None:
    with pytest.raises(ServiceUnavailableError) as exc_info:
        await Geocode(FakeGeocoding(unavailable=True), FakeCache())("Aalen")
    assert exc_info.value.code == "geocoding_unavailable"


async def test_reverse_uses_rounded_grid_only() -> None:
    geocoding = FakeGeocoding(reverse_result=AALEN)
    cache = FakeCache()
    use_case = ReverseGeocode(geocoding, cache)

    await use_case(GeoPoint(48.837123, 10.093456))
    await use_case(GeoPoint(48.83689, 10.09312))  # same ~100 m cell

    assert geocoding.reverse_calls == [GeoPoint(48.837, 10.093)]
    assert all("48.8371" not in key for key in cache.store)


async def test_reverse_without_result_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        await ReverseGeocode(FakeGeocoding(), FakeCache())(GeoPoint(0.0, 0.0))
