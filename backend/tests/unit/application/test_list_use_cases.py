"""Shared list use cases with fake adapters (R13)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

from stadtfest.application.collections.lists import (
    AddListEvent,
    AddListMember,
    CreateSharedList,
    DeleteSharedList,
    GetSharedList,
    ListSharedLists,
    RemoveListEvent,
    RemoveListMember,
    RenameSharedList,
)
from stadtfest.application.events.views import EventSummaryView
from stadtfest.application.shared.errors import InvalidInputError, NotFoundError
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import (
    FakeAccountResolver,
    FakeFriendRepository,
    FakeSharedListRepository,
    FixedClock,
)

LENA, TIM, MIA = (Principal(f"sub-{n}", frozenset({Role.USER})) for n in ("lena", "tim", "mia"))
LENA_ID, TIM_ID, MIA_ID = (uuid5(NAMESPACE_URL, p.subject) for p in (LENA, TIM, MIA))
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
TODAY = date(2026, 10, 9)


def _event(name: str, start: date, end: date) -> EventSummaryView:
    return EventSummaryView(
        id=uuid4(),
        name=name,
        short_name=name,
        status=EventStatus.PUBLISHED,
        start_date=start,
        end_date=end,
        place="Markt",
        city="Ulm",
        location=GeoPoint(48.4, 10.0),
        category_id=uuid4(),
    )


class Setup:
    def __init__(self) -> None:
        self.lists = FakeSharedListRepository(
            people={LENA_ID: ("Lena", "B"), TIM_ID: ("Tim", "K"), MIA_ID: ("Mia", "S")}
        )
        self.friends = FakeFriendRepository(people=dict.fromkeys([LENA_ID, TIM_ID], ("x", "y")))
        self.friends.friendships[frozenset({LENA_ID, TIM_ID})] = NOW  # Mia is no friend
        self.accounts = FakeAccountResolver()

    def create(self) -> CreateSharedList:
        return CreateSharedList(self.lists, self.friends, self.accounts, lambda: NOW)

    async def lena_list(self, *members: UUID) -> UUID:
        return (await self.create()(LENA, "Weihnachtsmarkt-Tour", list(members))).id


@pytest.fixture
def s() -> Setup:
    return Setup()


async def test_create_with_friends_notifies_only_new_members(s: Setup) -> None:
    created = await s.create()(LENA, "  Weihnachtsmarkt-Tour   2026 ", [TIM_ID, LENA_ID])

    assert created.name == "Weihnachtsmarkt-Tour 2026"
    assert [m.id for m in created.members] == [LENA_ID, TIM_ID]
    assert s.lists.added_events == [(created.id, [TIM_ID], LENA_ID)]


@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
async def test_invalid_names_are_rejected(s: Setup, name: str) -> None:
    with pytest.raises(InvalidInputError):
        await s.create()(LENA, name, [])


async def test_only_friends_can_be_added(s: Setup) -> None:
    with pytest.raises(InvalidInputError) as raised:
        await s.create()(LENA, "Liste", [MIA_ID])
    assert raised.value.code == "not_a_friend"
    list_id = await s.lena_list()
    with pytest.raises(InvalidInputError):
        await AddListMember(s.lists, s.friends, s.accounts, lambda: NOW)(LENA, list_id, MIA_ID)


async def test_non_members_get_404_everywhere(s: Setup) -> None:
    list_id = await s.lena_list()
    calls = [
        GetSharedList(s.lists, s.accounts)(MIA, list_id),
        RenameSharedList(s.lists, s.accounts)(MIA, list_id, "Neu"),
        DeleteSharedList(s.lists, s.accounts)(MIA, list_id),
        RemoveListMember(s.lists, s.accounts)(MIA, list_id, LENA_ID),
        AddListEvent(s.lists, s.accounts, lambda: NOW)(MIA, list_id, uuid4()),
        RemoveListEvent(s.lists, s.accounts)(MIA, list_id, uuid4()),
        AddListMember(s.lists, s.friends, s.accounts, lambda: NOW)(MIA, list_id, TIM_ID),
    ]
    for call in calls:
        with pytest.raises(NotFoundError):
            await call
    assert s.lists.names[list_id] == "Weihnachtsmarkt-Tour"


async def test_members_have_equal_rights(s: Setup) -> None:
    list_id = await s.lena_list(TIM_ID)
    renamed = await RenameSharedList(s.lists, s.accounts)(TIM, list_id, "Wiesn-Crew")
    assert renamed.name == "Wiesn-Crew"
    await DeleteSharedList(s.lists, s.accounts)(TIM, list_id)
    assert list_id not in s.lists.names


async def test_last_member_leaving_deletes_the_list(s: Setup) -> None:
    list_id = await s.lena_list(TIM_ID)
    remove = RemoveListMember(s.lists, s.accounts)
    await remove(TIM, list_id, TIM_ID)  # Tim leaves
    assert list_id in s.lists.names
    await remove(LENA, list_id, LENA_ID)  # the last one leaves
    assert list_id not in s.lists.names


async def test_events_only_public_idempotent_and_overview_sorted(s: Setup) -> None:
    advent = _event("Weihnachtsmarkt", date(2026, 11, 23), date(2026, 12, 22))
    over = _event("Herbstmarkt", date(2026, 9, 1), date(2026, 9, 3))
    soon = _event("Oktoberfest", date(2026, 10, 10), date(2026, 10, 12))
    s.lists.public_events = {e.id: e for e in (advent, over, soon)}
    first = await s.lena_list()
    second = (await s.create()(LENA, "A-Liste ohne Feste", [])).id
    add = AddListEvent(s.lists, s.accounts, lambda: NOW)
    for event in (advent, over, advent):
        await add(LENA, first, event.id)
    with pytest.raises(NotFoundError):
        await add(LENA, first, uuid4())  # not public

    third = (await s.create()(LENA, "Wiesn", [])).id
    await add(LENA, third, soon.id)
    overview = await ListSharedLists(s.lists, s.accounts, FixedClock(TODAY))(LENA)

    assert [item.list.id for item in overview] == [third, first, second]
    by_id = {item.list.id: item for item in overview}
    assert [e.event.name for e in by_id[first].list.events] == ["Herbstmarkt", "Weihnachtsmarkt"]
    assert by_id[first].next_event is not None
    assert by_id[first].next_event.event.name == "Weihnachtsmarkt"
    assert by_id[second].next_event is None
    await RemoveListEvent(s.lists, s.accounts)(LENA, first, advent.id)
    assert s.lists.events[first] == [over.id]
