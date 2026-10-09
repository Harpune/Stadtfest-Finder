"""Shared list repository against PostgreSQL (R13)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.lists import SqlSharedListRepository
from stadtfest.adapters.outbound.persistence.models import (
    EventRow,
    OutboxRow,
    SharedListRow,
)
from stadtfest.adapters.outbound.persistence.notifications import SqlNotificationStore
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.domain.notifications.notification import ListFacts, NotificationType
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


@pytest.fixture(scope="module")
def lists(sessions: async_sessionmaker[AsyncSession]) -> SqlSharedListRepository:
    return SqlSharedListRepository(sessions, ImageUrls("https://img.test/x"))


async def _user(sessions: async_sessionmaker[AsyncSession], first: str) -> tuple[str, UUID]:
    subject = f"sub-{uuid4()}"
    record = await SqlUserRepository(sessions).get_or_create(subject, first, "Test")
    return subject, record.id


async def _public_events(sessions: async_sessionmaker[AsyncSession], n: int) -> list[UUID]:
    async with sessions() as session:
        return list(
            await session.scalars(
                select(EventRow.id)
                .where(EventRow.status == "published", EventRow.deleted_at.is_(None))
                .order_by(EventRow.start_date)
                .limit(n)
            )
        )


async def test_create_view_and_outbox(
    sessions: async_sessionmaker[AsyncSession], lists: SqlSharedListRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    _, tim = await _user(sessions, "Tim")
    list_id = uuid4()
    await lists.create(list_id, "Tour", lena, [tim], NOW)
    first, second = await _public_events(sessions, 2)
    assert await lists.add_event(list_id, second, tim, NOW)
    assert await lists.add_event(list_id, first, lena, NOW)
    assert await lists.add_event(list_id, first, lena, NOW)  # idempotent
    assert not await lists.add_event(list_id, uuid4(), lena, NOW)

    view = await lists.get(list_id)
    assert view is not None
    assert [m.first_name for m in view.members] == ["Lena", "Tim"]
    assert [e.event.id for e in view.events] == [first, second]
    assert view.events[0].emoji
    assert await lists.is_member(list_id, tim)
    assert [v.id for v in await lists.lists_of(tim)] == [list_id]
    async with sessions() as session:
        payload = await session.scalar(
            select(OutboxRow.payload).where(
                OutboxRow.type == "list.members_added",
                OutboxRow.payload["listId"].astext == str(list_id),
            )
        )
    assert payload == {"listId": str(list_id), "userIds": [str(tim)], "actorId": str(lena)}


async def test_deleted_events_disappear_from_lists(
    sessions: async_sessionmaker[AsyncSession], lists: SqlSharedListRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    list_id = uuid4()
    await lists.create(list_id, "Tour", lena, [], NOW)
    [event_id] = await _public_events(sessions, 1)
    await lists.add_event(list_id, event_id, lena, NOW)
    async with sessions.begin() as session:
        await session.execute(
            update(EventRow).where(EventRow.id == event_id).values(deleted_at=NOW)
        )
    try:
        view = await lists.get(list_id)
        assert view is not None
        assert view.events == []
    finally:
        async with sessions.begin() as session:
            await session.execute(
                update(EventRow).where(EventRow.id == event_id).values(deleted_at=None)
            )


async def test_parallel_adds_and_removes_by_two_members(
    sessions: async_sessionmaker[AsyncSession], lists: SqlSharedListRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    _, tim = await _user(sessions, "Tim")
    list_id = uuid4()
    await lists.create(list_id, "Tour", lena, [tim], NOW)
    events = await _public_events(sessions, 6)
    await asyncio.gather(
        *(lists.add_event(list_id, e, lena if i % 2 else tim, NOW) for i, e in enumerate(events))
    )
    await asyncio.gather(
        lists.remove_event(list_id, events[0]),
        lists.remove_event(list_id, events[1]),
        lists.add_event(list_id, events[0], tim, NOW + timedelta(seconds=1)),
    )
    view = await lists.get(list_id)
    assert view is not None
    assert len(view.events) in {4, 5}  # the re-add may win or lose against the removal
    assert events[1] not in {e.event.id for e in view.events}


async def test_last_member_leaving_deletes_the_list(
    sessions: async_sessionmaker[AsyncSession], lists: SqlSharedListRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    _, tim = await _user(sessions, "Tim")
    list_id = uuid4()
    await lists.create(list_id, "Tour", lena, [tim], NOW)
    await asyncio.gather(lists.remove_member(list_id, lena), lists.remove_member(list_id, tim))
    assert await lists.get(list_id) is None


async def test_account_deletion_and_list_added_notification(
    sessions: async_sessionmaker[AsyncSession], lists: SqlSharedListRepository
) -> None:
    lena_subject, lena = await _user(sessions, "Lena")
    tim_subject, tim = await _user(sessions, "Tim")
    shared, alone = uuid4(), uuid4()
    await lists.create(shared, "Gemeinsam", lena, [tim], NOW)
    await lists.create(alone, "Allein", lena, [], NOW)
    store = SqlNotificationStore(sessions)
    await store.add([tim], NotificationType.LIST_ADDED, shared, f"l:{shared}", NOW, actor_id=lena)
    [entry] = await store.page(tim, None, 10)
    assert entry.facts == ListFacts("Gemeinsam", "Lena")

    assert await SqlUserRepository(sessions).delete_personal_data(lena_subject)

    async with sessions() as session:
        remaining = await session.scalar(
            select(func.count()).select_from(SharedListRow).where(SharedListRow.id == alone)
        )
        creator = await session.scalar(
            select(SharedListRow.created_by).where(SharedListRow.id == shared)
        )
    assert remaining == 0  # nobody left in it
    assert creator is None
    view = await lists.get(shared)
    assert view is not None
    assert [m.id for m in view.members] == [tim]
    # The notification named Lena as actor: it goes with her account.
    assert await store.page(tim, None, 10) == []
    assert await SqlUserRepository(sessions).delete_personal_data(tim_subject)
    assert await lists.get(shared) is None
