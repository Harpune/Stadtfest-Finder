from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest

from stadtfest.application.events.criteria import PageCursor, SearchFilter
from stadtfest.application.events.use_cases import (
    CATALOG_NAMESPACE,
    CATEGORIES_NAMESPACE,
    CountEvents,
    GetPublicEvent,
    ListActiveCategories,
    SearchEvents,
)
from stadtfest.application.events.views import CategoryView, EventCountView, EventSummaryView
from stadtfest.application.shared.errors import InvalidInputError, NotFoundError
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.events.time_filter import DateRange, TimeFilter, TimeFilterKind
from tests.fakes import FakeCache, FakeCategoryCatalog, FakeEventCatalog, FixedClock

TODAY = date(2026, 9, 25)
CATEGORY = UUID("00000000-0000-0000-0000-00000000000a")


def _event(name: str, start_offset: int, days: int = 2) -> EventSummaryView:
    start = TODAY + timedelta(days=start_offset)
    return EventSummaryView(
        id=uuid4(),
        name=name,
        short_name=name[:18],
        status=EventStatus.PUBLISHED,
        start_date=start,
        end_date=start + timedelta(days=days),
        place="Marktplatz",
        city="Aalen",
        location=GeoPoint(48.84, 10.09),
        category_id=CATEGORY,
        distance_km=1.2,
    )


def _search(catalog: FakeEventCatalog, cache: FakeCache | None = None) -> SearchEvents:
    return SearchEvents(catalog, cache or FakeCache(), FixedClock(TODAY))


async def test_resolves_time_filter_against_today() -> None:
    catalog = FakeEventCatalog()
    await _search(catalog)(SearchFilter(time=TimeFilter(TimeFilterKind.TODAY)))
    criteria = catalog.search_calls[0][0]
    assert criteria.today == TODAY
    assert criteria.windows == (DateRange(TODAY, TODAY),)


async def test_next_cursor_points_after_last_item() -> None:
    rows = [_event("A", -1), _event("B", 3), _event("C", 5)]
    catalog = FakeEventCatalog(rows=rows)

    page = await _search(catalog)(SearchFilter(), limit=2)

    assert [item.name for item in page.items] == ["A", "B"]
    assert page.next_cursor is not None
    cursor = PageCursor.decode(page.next_cursor)
    assert cursor == PageCursor(
        upcoming=True, start_date=rows[1].start_date, name="B", id=rows[1].id
    )
    assert catalog.search_calls[0][2] == 3  # fetches one extra row to detect the next page


async def test_last_page_has_no_cursor() -> None:
    page = await _search(FakeEventCatalog(rows=[_event("A", 1)]))(SearchFilter(), limit=2)
    assert page.next_cursor is None


async def test_invalid_cursor_is_a_validation_error() -> None:
    with pytest.raises(InvalidInputError) as exc_info:
        await _search(FakeEventCatalog())(SearchFilter(), cursor="not-a-cursor")
    assert exc_info.value.fields == {"cursor": "invalid"}


async def test_guest_searches_are_cached_until_the_catalog_changes() -> None:
    catalog = FakeEventCatalog(rows=[_event("A", 1)])
    cache = FakeCache()
    search = _search(catalog, cache)
    search_filter = SearchFilter(reference=GeoPoint(48.8371, 10.0934))

    first = await search(search_filter)
    second = await search(search_filter)
    assert first == second
    assert len(catalog.search_calls) == 1
    assert 300 in cache.ttls.values()

    await cache.bump_generation(CATALOG_NAMESPACE)
    await search(search_filter)
    assert len(catalog.search_calls) == 2


async def test_cache_keys_do_not_contain_exact_coordinates() -> None:
    cache = FakeCache()
    await _search(FakeEventCatalog(), cache)(SearchFilter(reference=GeoPoint(48.83712, 10.09341)))
    assert all("48.837" not in key and "10.093" not in key for key in cache.store)


async def test_authenticated_searches_are_not_cached() -> None:
    catalog = FakeEventCatalog()
    cache = FakeCache()
    await _search(catalog, cache)(SearchFilter(), cacheable=False)
    assert cache.store == {}


async def test_count_is_cached() -> None:
    catalog = FakeEventCatalog(counts=EventCountView(total=3, by_category={CATEGORY: 3}))
    count = CountEvents(catalog, FakeCache(), FixedClock(TODAY))

    assert (await count(SearchFilter())).by_category == {CATEGORY: 3}
    assert (await count(SearchFilter())).total == 3
    assert catalog.count_calls == 1


async def test_categories_are_cached_with_etag_and_invalidated_by_generation() -> None:
    catalog = FakeCategoryCatalog(
        categories=[CategoryView(CATEGORY, "Stadtfest", "🎪", "#FFB547", 0)]
    )
    cache = FakeCache()
    use_case = ListActiveCategories(catalog, cache)

    first = await use_case()
    second = await use_case()
    assert first.etag == second.etag
    assert first.etag.startswith('"')
    assert catalog.calls == 1

    catalog.categories = [CategoryView(CATEGORY, "Stadtfeste", "🎪", "#FFB547", 0)]
    await cache.bump_generation(CATEGORIES_NAMESPACE)
    third = await use_case()
    assert third.etag != first.etag
    assert third.categories[0].name == "Stadtfeste"


def test_search_filter_validation() -> None:
    with pytest.raises(ValueError, match="radius"):
        SearchFilter(radius_km=5)
    with pytest.raises(ValueError, match="too short"):
        SearchFilter(text=" a ")
    with pytest.raises(ValueError, match="control"):
        SearchFilter(text="Aa\x00len")


def test_cursor_roundtrip_and_rejects_nul() -> None:
    cursor = PageCursor(upcoming=False, start_date=TODAY, name="Kalter Markt", id=uuid4())
    assert PageCursor.decode(cursor.encode()) == cursor
    evil = PageCursor(upcoming=False, start_date=TODAY, name="a\x00b", id=uuid4()).encode()
    with pytest.raises(ValueError, match="cursor"):
        PageCursor.decode(evil)


async def test_get_public_event_not_found() -> None:
    with pytest.raises(NotFoundError):
        await GetPublicEvent(FakeEventCatalog())(uuid4())
