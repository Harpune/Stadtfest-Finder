from datetime import date
from uuid import UUID, uuid4

import pytest

from stadtfest.application.collections.use_cases import (
    AddFavorite,
    IsFavorite,
    ListFavorites,
    RemoveFavorite,
)
from stadtfest.application.events.views import EventSummaryView
from stadtfest.application.shared.errors import NotFoundError
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import FakeAccountResolver, FakeFavoriteRepository, FixedClock

TODAY = date(2026, 9, 25)
LENA = Principal("sub-lena", frozenset({Role.USER}))


def _event(start: date, end: date, name: str = "Fest") -> EventSummaryView:
    return EventSummaryView(
        id=uuid4(),
        name=name,
        short_name=name,
        status=EventStatus.PUBLISHED,
        start_date=start,
        end_date=end,
        place="Marktplatz",
        city="Aalen",
        location=GeoPoint(48.8, 10.1),
        category_id=uuid4(),
    )


def _repository(*events: EventSummaryView) -> FakeFavoriteRepository:
    return FakeFavoriteRepository(public={event.id: event for event in events})


async def test_add_is_idempotent_and_counts_once() -> None:
    event = _event(TODAY, TODAY)
    favorites, accounts = _repository(event), FakeAccountResolver()
    add = AddFavorite(favorites, accounts)

    await add(LENA, event.id)
    await add(LENA, event.id)

    assert favorites.favorites == {"sub-lena": [event.id]}
    assert favorites.counts[event.id] == 1
    assert accounts.ensured == ["sub-lena", "sub-lena"]  # the account exists before the insert


async def test_add_rejects_events_that_are_not_public() -> None:
    with pytest.raises(NotFoundError):
        await AddFavorite(_repository(), FakeAccountResolver())(LENA, uuid4())


async def test_remove_is_idempotent() -> None:
    event = _event(TODAY, TODAY)
    favorites = _repository(event)
    await AddFavorite(favorites, FakeAccountResolver())(LENA, event.id)

    await RemoveFavorite(favorites)(LENA, event.id)
    await RemoveFavorite(favorites)(LENA, event.id)
    await RemoveFavorite(favorites)(LENA, UUID(int=0))

    assert favorites.favorites == {"sub-lena": []}
    assert favorites.counts[event.id] == 0


async def test_list_leaves_out_past_favorites_unless_requested() -> None:
    past = _event(date(2026, 7, 1), date(2026, 7, 5), "Ipfmesse")
    running = _event(date(2026, 9, 19), date(2026, 10, 4), "Oktoberfest")
    later = _event(date(2026, 11, 26), date(2026, 12, 23), "Weihnachtsmarkt")
    ending_today = _event(date(2026, 9, 20), TODAY, "Letzter Tag")
    favorites = _repository(past, running, later, ending_today)
    for event in (later, past, running, ending_today):
        await AddFavorite(favorites, FakeAccountResolver())(LENA, event.id)
    list_favorites = ListFavorites(favorites, FixedClock(TODAY))

    upcoming = await list_favorites(LENA, include_past=False)
    everything = await list_favorites(LENA, include_past=True)

    assert [f.event.name for f in upcoming] == ["Oktoberfest", "Letzter Tag", "Weihnachtsmarkt"]
    assert everything[0].event.name == "Ipfmesse"
    assert len(everything) == 4


async def test_is_favorite() -> None:
    event = _event(TODAY, TODAY)
    favorites = _repository(event)
    assert not await IsFavorite(favorites)(LENA, event.id)
    await AddFavorite(favorites, FakeAccountResolver())(LENA, event.id)
    assert await IsFavorite(favorites)(LENA, event.id)
