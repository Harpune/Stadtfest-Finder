"""Friend repository against PostgreSQL (R12): symmetry, outbox, cascade, notifications."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.friends import SqlFriendRepository
from stadtfest.adapters.outbound.persistence.models import (
    FriendLinkRow,
    FriendshipRow,
    OutboxRow,
)
from stadtfest.adapters.outbound.persistence.notifications import SqlNotificationStore
from stadtfest.domain.collections.friends import new_token
from stadtfest.domain.notifications.notification import NotificationType, PersonFacts
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), date(2026, 10, 9))
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _user(users: SqlUserRepository, first: str, last: str) -> tuple[str, UUID]:
    subject = f"sub-{uuid4()}"
    return subject, (await users.get_or_create(subject, first, last)).id


async def _count(sessions: async_sessionmaker[AsyncSession], query: object) -> int:
    async with sessions() as session:
        return int(await session.scalar(query) or 0)  # type: ignore[call-overload]


async def test_befriend_is_symmetric_idempotent_and_writes_one_event(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    users, friends = SqlUserRepository(sessions), SqlFriendRepository(sessions)
    _, lena = await _user(users, "Lena", "Beispiel")
    _, tim = await _user(users, "Tim", "Krause")
    token = new_token()
    await friends.set_link(lena, token, NOW)

    assert (await friends.owner_of(token)) is not None
    first = await friends.befriend(lena, tim, NOW)
    await friends.befriend(lena, tim, NOW)

    assert (first.id, first.first_name, first.last_name) == (lena, "Lena", "Beispiel")
    assert [f.id for f in await friends.friends_of(lena)] == [tim]
    assert [f.id for f in await friends.friends_of(tim)] == [lena]
    events = select(func.count()).where(
        OutboxRow.type == "friendship.created", OutboxRow.payload["userId"].astext == str(lena)
    )
    assert await _count(sessions, events) == 1

    await friends.set_link(lena, new_token(), NOW)
    assert await friends.owner_of(token) is None
    await friends.remove(tim, lena)
    assert await friends.friends_of(lena) == []
    assert await friends.friends_of(tim) == []


async def test_friend_added_lists_the_name_and_goes_with_the_account(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    users, friends = SqlUserRepository(sessions), SqlFriendRepository(sessions)
    store = SqlNotificationStore(sessions)
    lena_subject, lena = await _user(users, "Lena", "Beispiel")
    tim_subject, tim = await _user(users, "Tim", "Krause")
    await friends.set_link(lena, new_token(), NOW)
    await friends.befriend(lena, tim, NOW)
    await store.add([lena], NotificationType.FRIEND_ADDED, tim, f"friend_added:{tim}", NOW)

    [entry] = await store.page(lena, None, 10)
    assert entry.facts == PersonFacts("Tim", "Krause")
    assert entry.notification.subject_id == tim
    assert await store.unread_count(lena) == 1

    # Tim deletes his account: friendship and the notification naming him are gone.
    assert await users.delete_personal_data(tim_subject)
    assert await store.page(lena, None, 10) == []
    assert await friends.friends_of(lena) == []
    # Lena deletes hers: her link goes too.
    assert await users.delete_personal_data(lena_subject)
    links = select(func.count()).select_from(FriendLinkRow).where(FriendLinkRow.user_id == lena)
    rows = select(func.count()).select_from(FriendshipRow).where(FriendshipRow.friend_id == lena)
    assert await _count(sessions, links) == 0
    assert await _count(sessions, rows) == 0
