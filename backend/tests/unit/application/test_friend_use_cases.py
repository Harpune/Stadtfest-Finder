"""Friend use cases with fake adapters (R12)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import pytest

from stadtfest.application.collections.friends import (
    AcceptFriendLink,
    GetFriendLink,
    ListFriends,
    LookUpFriendLink,
    RemoveFriend,
    RotateFriendLink,
)
from stadtfest.application.shared.errors import (
    InvalidInputError,
    NotFoundError,
    TooManyRequestsError,
)
from stadtfest.domain.collections.friends import LOOKUP_LIMIT, is_token
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import FakeAccountResolver, FakeFriendRepository, FakeRateLimiter

LENA = Principal("sub-lena", frozenset({Role.USER}))
TIM = Principal("sub-tim", frozenset({Role.USER}))
LENA_ID = uuid5(NAMESPACE_URL, LENA.subject)
TIM_ID = uuid5(NAMESPACE_URL, TIM.subject)
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


@pytest.fixture
def friends() -> FakeFriendRepository:
    return FakeFriendRepository(people={LENA_ID: ("Lena", "beispiel"), TIM_ID: ("Tim", "Krause")})


async def _lena_link(friends: FakeFriendRepository) -> str:
    return (await GetFriendLink(friends, FakeAccountResolver(), lambda: NOW)(LENA)).token


async def test_link_is_created_once_and_has_no_personal_data(
    friends: FakeFriendRepository,
) -> None:
    get = GetFriendLink(friends, FakeAccountResolver(), lambda: NOW)
    first = await get(LENA)
    assert is_token(first.token)
    assert len(first.token) == 22
    assert "lena" not in first.token.lower()
    assert (await get(LENA)).token == first.token


async def test_rotate_invalidates_the_old_link(friends: FakeFriendRepository) -> None:
    old = await _lena_link(friends)
    new = (await RotateFriendLink(friends, FakeAccountResolver(), lambda: NOW)(LENA)).token
    look_up = LookUpFriendLink(friends, FakeAccountResolver(), FakeRateLimiter())
    assert new != old
    with pytest.raises(NotFoundError):
        await look_up(TIM, old)
    assert (await look_up(TIM, new)).first_name == "Lena"


async def test_look_up_shows_first_name_and_initial_only(friends: FakeFriendRepository) -> None:
    owner = await LookUpFriendLink(friends, FakeAccountResolver(), FakeRateLimiter())(
        TIM, await _lena_link(friends)
    )
    assert (owner.first_name, owner.last_name_initial) == ("Lena", "B")


async def test_accept_is_idempotent_and_rejects_the_own_link(
    friends: FakeFriendRepository,
) -> None:
    token = await _lena_link(friends)
    accept = AcceptFriendLink(friends, FakeAccountResolver(), FakeRateLimiter(), lambda: NOW)

    friend = await accept(TIM, token)
    await accept(TIM, token)

    assert (friend.id, friend.first_name) == (LENA_ID, "Lena")
    assert friends.created_events == [(LENA_ID, TIM_ID)]  # notified once
    with pytest.raises(InvalidInputError) as raised:
        await accept(LENA, token)
    assert raised.value.code == "self_link"
    with pytest.raises(NotFoundError):
        await accept(TIM, "A" * 22)
    with pytest.raises(NotFoundError):
        await accept(TIM, "kein-token")


async def test_guessing_is_rate_limited(friends: FakeFriendRepository) -> None:
    limiter = FakeRateLimiter()
    look_up = LookUpFriendLink(friends, FakeAccountResolver(), limiter)
    for _ in range(LOOKUP_LIMIT):
        with pytest.raises(NotFoundError):
            await look_up(TIM, "A" * 22)
    with pytest.raises(TooManyRequestsError):
        await look_up(TIM, await _lena_link(friends))


async def test_list_and_remove_on_both_sides(friends: FakeFriendRepository) -> None:
    accept = AcceptFriendLink(friends, FakeAccountResolver(), FakeRateLimiter(), lambda: NOW)
    await accept(TIM, await _lena_link(friends))
    list_friends = ListFriends(friends, FakeAccountResolver())
    assert [f.first_name for f in await list_friends(LENA)] == ["Tim"]
    assert [f.first_name for f in await list_friends(TIM)] == ["Lena"]

    await RemoveFriend(friends, FakeAccountResolver())(TIM, LENA_ID)
    await RemoveFriend(friends, FakeAccountResolver())(TIM, LENA_ID)  # idempotent

    assert await list_friends(LENA) == []
    assert await list_friends(TIM) == []
