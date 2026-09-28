"""REST adapter tests: routers + real use cases over in-memory fakes (no database)."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stadtfest.adapters.inbound.rest import categories, events, geocoding
from stadtfest.adapters.inbound.rest.errors import register_error_handlers
from stadtfest.application.events.use_cases import (
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventDetailView,
    EventSummaryView,
    ProgramItemView,
)
from stadtfest.application.geocoding.ports import Place, PlaceKind
from stadtfest.application.geocoding.use_cases import Geocode, ReverseGeocode
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.events.time_filter import TimeFilterKind
from tests.fakes import FakeCache, FakeCategoryCatalog, FakeEventCatalog, FakeGeocoding, FixedClock

TODAY = date(2026, 9, 25)
CATEGORY = CategoryView(
    UUID("00000000-0000-0000-0000-00000000000a"), "Stadtfest", "🎪", "#FFB547", 0
)


@dataclass
class FakeRedis:
    counters: dict[str, int] = field(default_factory=dict)

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True


def _summary(name: str = "Reichsstädter Tage") -> EventSummaryView:
    return EventSummaryView(
        id=uuid4(),
        name=name,
        short_name="Reichsstädter",
        status=EventStatus.CANCELLED,
        start_date=TODAY - timedelta(days=2),
        end_date=TODAY + timedelta(days=2),
        place="Marktplatz",
        city="Aalen",
        location=GeoPoint(48.8368, 10.0932),
        category_id=CATEGORY.id,
        distance_km=1.4,
    )


def _detail(event_id: UUID) -> EventDetailView:
    return EventDetailView(
        id=event_id,
        name="Reichsstädter Tage",
        short_name="Reichsstädter",
        status=EventStatus.PUBLISHED,
        cancel_reason=None,
        category=CATEGORY,
        start_date=TODAY,
        end_date=TODAY + timedelta(days=2),
        opening_hours=("Fr 18-24 Uhr",),
        price="Frei",
        place="Marktplatz",
        address="Marktplatz 1",
        city="Aalen",
        postal_code="73430",
        location=GeoPoint(48.8368, 10.0932),
        description="Stadtfest",
        program=(ProgramItemView(TODAY, "10:45 Uhr", "Umzug", None),),
        transit=None,
        parking=None,
        website_url="https://example.test/fest",
    )


@pytest.fixture
def catalog() -> FakeEventCatalog:
    return FakeEventCatalog(
        rows=[_summary()], counts=EventCountView(total=1, by_category={CATEGORY.id: 1})
    )


@pytest.fixture
def geo() -> FakeGeocoding:
    aalen = Place("73430 Aalen", "Aalen", GeoPoint(48.8375, 10.0933), PlaceKind.POSTCODE, "73430")
    return FakeGeocoding(places=[aalen], reverse_result=aalen)


@pytest.fixture
def client(catalog: FakeEventCatalog, geo: FakeGeocoding) -> TestClient:
    cache = FakeCache()
    clock = FixedClock(TODAY)
    app = FastAPI()
    register_error_handlers(app)
    for router in (categories.router, events.router, geocoding.router):
        app.include_router(router)
    app.state.container = SimpleNamespace(
        redis=FakeRedis(),
        search_events=SearchEvents(catalog, cache, clock),
        count_events=CountEvents(catalog, cache, clock),
        get_public_event=GetPublicEvent(catalog),
        list_active_categories=ListActiveCategories(FakeCategoryCatalog([CATEGORY]), cache),
        geocode=Geocode(geo, cache),
        reverse_geocode=ReverseGeocode(geo, cache),
    )
    return TestClient(app)


def test_search_returns_camel_case_summaries(client: TestClient) -> None:
    response = client.get("/v1/events", params={"lat": 48.84, "lon": 10.09, "radiusKm": 50})
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["shortName"] == "Reichsstädter"
    assert item["status"] == "cancelled"
    assert item["distanceKm"] == 1.4
    assert response.json()["nextCursor"] is None


def test_search_parses_csv_filters(client: TestClient, catalog: FakeEventCatalog) -> None:
    category = str(CATEGORY.id)
    response = client.get(
        "/v1/events",
        params={
            "bbox": "9.5,48.5,10.5,49.2",
            "when": "months",
            "months": "2026-10,2026-12",
            "categories": category,
            "q": "Aalen",
        },
    )
    assert response.status_code == 200
    criteria = catalog.search_calls[0][0]
    assert criteria.filter.bbox is not None
    assert criteria.filter.time.kind is TimeFilterKind.MONTHS
    assert criteria.windows is not None
    assert len(criteria.windows) == 2
    assert criteria.filter.category_ids == frozenset({CATEGORY.id})


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"lat": 48.8}, "lon"),
        ({"lon": 10.1}, "lat"),
        ({"bbox": "1,2,3"}, "bbox"),
        ({"bbox": "11,48,10,49"}, "bbox"),
        ({"when": "months"}, "months"),
        ({"when": "months", "months": "2026-13"}, "months"),
        ({"categories": "not-a-uuid"}, "categories"),
        ({"q": "  a "}, "q"),
        ({"q": "Aa\x00len"}, "q"),
        ({"radiusKm": 5}, "radiusKm"),
        ({"cursor": "garbage"}, "cursor"),
    ],
)
def test_invalid_filters_are_422_with_field(
    client: TestClient, params: dict[str, object], field: str
) -> None:
    response = client.get("/v1/events", params=params)
    assert response.status_code == 422
    assert response.json()["error"] == "validation_failed"
    assert field in response.json()["fields"]


def test_count(client: TestClient) -> None:
    response = client.get("/v1/events/count", params={"when": "today"})
    assert response.json() == {"total": 1, "byCategory": {str(CATEGORY.id): 1}}


def test_event_detail_and_404(client: TestClient, catalog: FakeEventCatalog) -> None:
    event_id = uuid4()
    catalog.details[event_id] = _detail(event_id)

    body = client.get(f"/v1/events/{event_id}").json()
    assert body["category"]["name"] == "Stadtfest"
    assert body["program"][0]["timeLabel"] == "10:45 Uhr"
    assert body["postalCode"] == "73430"

    missing = client.get(f"/v1/events/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"


def test_categories_etag_and_304(client: TestClient) -> None:
    first = client.get("/v1/categories")
    assert first.status_code == 200
    assert first.json()[0] == {
        "id": str(CATEGORY.id),
        "name": "Stadtfest",
        "emoji": "🎪",
        "color": "#FFB547",
        "sortOrder": 0,
    }
    assert first.headers["cache-control"] == "public, max-age=900"
    etag = first.headers["etag"]

    second = client.get("/v1/categories", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.headers["etag"] == etag


def test_geocode_and_reverse(client: TestClient) -> None:
    results = client.get("/v1/geocode", params={"q": "73430"}).json()
    assert results[0] == {
        "label": "73430 Aalen",
        "postalCode": "73430",
        "city": "Aalen",
        "lat": 48.8375,
        "lon": 10.0933,
        "kind": "postcode",
    }
    reverse = client.get("/v1/geocode/reverse", params={"lat": 48.8371, "lon": 10.0931})
    assert reverse.json() == {"postalCode": "73430", "city": "Aalen", "label": "73430 Aalen"}


def test_geocode_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stadtfest.adapters.inbound.rest.rate_limit.time.time", lambda: 1000.0)
    statuses = [client.get("/v1/geocode", params={"q": "Aalen"}).status_code for _ in range(6)]
    assert statuses == [200, 200, 200, 200, 200, 429]

    limited = client.get("/v1/geocode", params={"q": "Aalen"})
    assert limited.headers["retry-after"] == "1"
    assert limited.json()["error"] == "rate_limited"

    monkeypatch.setattr("stadtfest.adapters.inbound.rest.rate_limit.time.time", lambda: 1001.0)
    assert client.get("/v1/geocode", params={"q": "Aalen"}).status_code == 200


def test_geocode_unavailable_is_503(client: TestClient, geo: FakeGeocoding) -> None:
    geo.unavailable = True
    response = client.get("/v1/geocode", params={"q": "Ulm"})
    assert response.status_code == 503
    assert response.json()["error"] == "geocoding_unavailable"
