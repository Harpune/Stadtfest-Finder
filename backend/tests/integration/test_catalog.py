"""SqlCatalog against PostGIS with the synthetic seed (fixed reference day)."""

from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.events.criteria import PageCursor, SearchCriteria, SearchFilter
from stadtfest.domain.events.geo import BoundingBox, GeoPoint
from stadtfest.domain.events.time_filter import TimeFilter, TimeFilterKind, YearMonth
from tests.integration.seed_support import (
    CATEGORIES,
    EVENTS,
    end_date,
    haversine_km,
    listed,
    load,
    seed_id,
    start_date,
)

TEST_URLS = ImageUrls("https://img.test/stadtfest-images")

pytestmark = pytest.mark.integration

TODAY = date(2026, 9, 25)  # Friday
AALEN = GeoPoint(48.8375, 10.0933)


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def catalog(engine: AsyncEngine) -> SqlCatalog:
    return SqlCatalog(
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), TEST_URLS
    )


def _criteria(**kwargs: object) -> SearchCriteria:
    return SearchCriteria.resolve(SearchFilter(**kwargs), TODAY)  # type: ignore[arg-type]


def _expected_order(events: list) -> list[str]:  # type: ignore[type-arg]
    def key(e):  # type: ignore[no-untyped-def]
        start = start_date(e, TODAY)
        return (start > TODAY, start, e.name)

    return [e.name for e in sorted(events, key=key)]


async def test_lists_only_public_not_ended_events_in_public_order(catalog: SqlCatalog) -> None:
    rows = await catalog.search(_criteria(), None, 500)

    assert [r.name for r in rows] == _expected_order(listed(TODAY))
    assert all(r.status.value in {"published", "cancelled"} for r in rows)
    assert "Lichterfest Oberkochen" not in {r.name for r in rows}  # draft
    assert "Aalener Frühlingsfest" not in {r.name for r in rows}  # past


async def test_keyset_paging_returns_the_same_sequence(catalog: SqlCatalog) -> None:
    full = [r.id for r in await catalog.search(_criteria(), None, 500)]
    paged: list = []  # type: ignore[type-arg]
    cursor = None
    while True:
        page = await catalog.search(_criteria(), cursor, 7)
        paged.extend(r.id for r in page)
        if len(page) < 7:
            break
        last = page[-1]
        cursor = PageCursor(last.start_date > TODAY, last.start_date, last.name, last.id)
    assert paged == full


async def test_radius_search_and_distances(catalog: SqlCatalog) -> None:
    radius = 12
    rows = await catalog.search(_criteria(reference=AALEN, radius_km=radius), None, 500)
    by_name = {r.name: r for r in rows}

    for event in listed(TODAY):
        assert event.lat is not None
        assert event.lon is not None
        distance = haversine_km(AALEN.lat, AALEN.lon, event.lat, event.lon)
        if abs(distance - radius) < 0.3:
            continue  # spheroid vs. sphere: skip events right at the boundary
        assert (event.name in by_name) == (distance < radius), event.name
        if event.name in by_name:
            assert by_name[event.name].distance_km == pytest.approx(distance, abs=0.2)


async def test_bbox_distance_refers_to_center(catalog: SqlCatalog) -> None:
    box = BoundingBox(9.9, 48.7, 10.3, 49.0)
    rows = await catalog.search(_criteria(bbox=box), None, 500)
    assert rows
    assert all(9.9 <= r.location.lon <= 10.3 and 48.7 <= r.location.lat <= 49.0 for r in rows)
    assert all(r.distance_km is not None for r in rows)


async def test_today_weekend_and_months(catalog: SqlCatalog) -> None:
    today_rows = await catalog.search(_criteria(time=TimeFilter(TimeFilterKind.TODAY)), None, 500)
    expected_today = {
        e.name for e in listed(TODAY) if start_date(e, TODAY) <= TODAY <= end_date(e, TODAY)
    }
    assert {r.name for r in today_rows} == expected_today

    saturday, sunday = TODAY + timedelta(days=1), TODAY + timedelta(days=2)
    weekend_rows = await catalog.search(
        _criteria(time=TimeFilter(TimeFilterKind.WEEKEND)), None, 500
    )
    expected_weekend = {
        e.name
        for e in listed(TODAY)
        if start_date(e, TODAY) <= sunday and end_date(e, TODAY) >= saturday
    }
    assert {r.name for r in weekend_rows} == expected_weekend

    december = YearMonth(2026, 12)
    month_rows = await catalog.search(
        _criteria(time=TimeFilter(TimeFilterKind.MONTHS, (december,))), None, 500
    )
    window = december.as_range()
    expected_months = {
        e.name
        for e in listed(TODAY)
        if start_date(e, TODAY) <= window.end and end_date(e, TODAY) >= window.start
    }
    assert {r.name for r in month_rows} == expected_months
    assert "Aalener Weihnachtsmarkt" in expected_months


async def test_category_filter_ignores_inactive_and_unknown(catalog: SqlCatalog) -> None:
    christmas = seed_id("category", "weihnachtsmarkt")
    inactive = seed_id("category", "weinfest")
    unknown = seed_id("category", "does-not-exist")

    only_christmas = await catalog.search(_criteria(category_ids=frozenset({christmas})), None, 500)
    assert only_christmas
    assert {r.category_id for r in only_christmas} == {christmas}

    mixed = await catalog.search(
        _criteria(category_ids=frozenset({christmas, inactive, unknown})), None, 500
    )
    assert {r.id for r in mixed} == {r.id for r in only_christmas}

    ignored = await catalog.search(
        _criteria(category_ids=frozenset({inactive, unknown})), None, 500
    )
    assert len(ignored) == len(listed(TODAY))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Reichstaedter", "Reichsstädter Tage"),  # typo + umlaut
        ("REICHSSTÄDTER", "Reichsstädter Tage"),
        ("gmund", "Gmünder Stadtfest"),  # accent-insensitive, city match
        ("Kalter Markt", "Kalter Markt"),
    ],
)
async def test_text_search(catalog: SqlCatalog, text: str, expected: str) -> None:
    rows = await catalog.search(_criteria(text=text), None, 500)
    assert expected in {r.name for r in rows}


async def test_counts_by_category_ignore_the_category_filter(catalog: SqlCatalog) -> None:
    christmas = seed_id("category", "weihnachtsmarkt")
    counts = await catalog.count(_criteria(category_ids=frozenset({christmas})))

    all_listed = listed(TODAY)
    assert counts.total == sum(1 for e in all_listed if e.category == "weihnachtsmarkt")
    for category in CATEGORIES:
        expected = sum(1 for e in all_listed if e.category == category.key)
        assert counts.by_category.get(seed_id("category", category.key), 0) == expected


async def test_get_public_detail(catalog: SqlCatalog) -> None:
    event = await catalog.get_public(seed_id("event", "reichsstaedter-tage"), AALEN)
    assert event is not None
    assert event.category.name == "Stadtfest"
    assert [p.title for p in event.program][:2] == [
        "Eröffnung mit Fassanstich",
        "Historischer Umzug",
    ]
    assert event.distance_km is not None
    assert event.distance_km < 1

    past = await catalog.get_public(seed_id("event", "aalener-fruehlingsfest"), None)
    assert past is not None  # past events stay reachable by ID

    assert await catalog.get_public(seed_id("event", "oberkochener-lichterfest"), None) is None
    cancelled = await catalog.get_public(seed_id("event", "neresheimer-klosterfest"), None)
    assert cancelled is not None
    assert cancelled.cancel_reason


async def test_active_categories_in_order(catalog: SqlCatalog) -> None:
    categories = await catalog.list_active()
    assert [c.name for c in categories] == [c.name for c in CATEGORIES if c.active]


def test_seed_is_consistent() -> None:
    keys = [e.key for e in EVENTS]
    assert len(keys) == len(set(keys))
