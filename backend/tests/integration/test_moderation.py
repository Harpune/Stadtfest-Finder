"""Moderation persistence and outbox against PostgreSQL and Redis (R07)."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.models import (
    FavoriteRow,
    OutboxRow,
)
from stadtfest.adapters.outbound.persistence.moderation import (
    SqlActiveCategories,
    SqlManagedEventRepository,
)
from stadtfest.adapters.outbound.persistence.outbox import SqlEventFavorites, SqlOutboxStore
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.moderation.ports import VersionConflictError
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent, PurgeOutbox, RelayOutbox
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.maintenance import EventContent, ManagedEvent, ProgramEntry
from tests.integration.seed_support import load

TEST_URLS = ImageUrls("https://img.test/stadtfest-images")

pytestmark = pytest.mark.integration

TODAY = date(2026, 9, 25)
NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="module")
def repo(sessions: async_sessionmaker[AsyncSession]) -> SqlManagedEventRepository:
    return SqlManagedEventRepository(sessions)


@pytest.fixture
async def user(sessions: async_sessionmaker[AsyncSession]) -> UUID:
    return (await SqlUserRepository(sessions).get_or_create(f"sub-{uuid4()}", "Mia", "M")).id


async def _clear_outbox(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions.begin() as session:
        await session.execute(
            update(OutboxRow).where(OutboxRow.dispatched_at.is_(None)).values(dispatched_at=NOW)
        )


async def _new_event(
    sessions: async_sessionmaker[AsyncSession], repo: SqlManagedEventRepository, user: UUID
) -> ManagedEvent:
    categories = await SqlActiveCategories(sessions).active_ids()
    content = EventContent(
        name="Herbstfest Wasseralfingen",
        category_id=next(iter(categories)),
        start_date=date(2026, 10, 17),
        end_date=date(2026, 10, 18),
        place="Festplatz",
        address="Wasseralfingen",
        city="Aalen",
        postal_code="73430",
        lat=48.86,
        lon=10.1,
        program=(ProgramEntry(date(2026, 10, 17), "11 Uhr", "Fassanstich"),),
    ).with_defaults()
    event = ManagedEvent(uuid4(), EventStatus.DRAFT, content)
    await repo.add(event, user)
    return event


async def test_add_get_and_list(
    sessions: async_sessionmaker[AsyncSession], repo: SqlManagedEventRepository, user: UUID
) -> None:
    event = await _new_event(sessions, repo, user)

    loaded = await repo.get(event.id)

    assert loaded is not None
    assert loaded.content == event.content
    assert loaded.version == 1
    assert loaded.content.program[0].title == "Fassanstich"
    listed = await repo.list_events(frozenset({event.id, uuid4()}))
    assert [row.id for row in listed] == [event.id]


async def test_optimistic_lock(
    sessions: async_sessionmaker[AsyncSession], repo: SqlManagedEventRepository, user: UUID
) -> None:
    event = await _new_event(sessions, repo, user)
    first = await repo.get(event.id)
    second = await repo.get(event.id)
    assert first is not None
    assert second is not None

    first.edit(replace(first.content, price="Frei"))
    assert await repo.save(first, 1, user) == 2

    second.edit(replace(second.content, price="5 €"))
    with pytest.raises(VersionConflictError):
        await repo.save(second, 1, user)
    stored = await repo.get(event.id)
    assert stored is not None
    assert stored.content.price == "Frei"


async def test_parallel_saves_with_the_same_version_let_one_win(
    sessions: async_sessionmaker[AsyncSession], repo: SqlManagedEventRepository, user: UUID
) -> None:
    event = await _new_event(sessions, repo, user)
    copies = [await repo.get(event.id) for _ in range(4)]

    async def attempt(index: int) -> bool:
        copy = copies[index]
        assert copy is not None
        copy.edit(replace(copy.content, price=f"{index} €"))
        try:
            await repo.save(copy, 1, user)
        except VersionConflictError:
            return False
        return True

    results = await asyncio.gather(*(attempt(i) for i in range(4)))
    assert results.count(True) == 1


async def test_publish_writes_the_outbox_in_the_same_transaction(
    sessions: async_sessionmaker[AsyncSession], repo: SqlManagedEventRepository, user: UUID
) -> None:
    await _clear_outbox(sessions)
    event = await _new_event(sessions, repo, user)
    loaded = await repo.get(event.id)
    assert loaded is not None
    loaded.publish(await SqlActiveCategories(sessions).active_ids(), NOW)
    await repo.save(loaded, 1, user)

    # A failing save (stale version) must not leave an outbox entry behind.
    stale = await repo.get(event.id)
    assert stale is not None
    stale.unpublish()
    with pytest.raises(VersionConflictError):
        await repo.save(stale, 1, user)

    async with sessions() as session:
        types = (
            await session.scalars(select(OutboxRow.type).where(OutboxRow.dispatched_at.is_(None)))
        ).all()
    assert types == ["event.published"]


async def test_relay_consumer_invalidates_the_cache_and_cleans_up_favorites(
    sessions: async_sessionmaker[AsyncSession],
    repo: SqlManagedEventRepository,
    user: UUID,
    redis_url: str,
) -> None:
    await _clear_outbox(sessions)
    client = Redis.from_url(redis_url, decode_responses=True)
    cache = RedisCache(client, prefix=f"test-{uuid4()}:")
    event = await _new_event(sessions, repo, user)
    loaded = await repo.get(event.id)
    assert loaded is not None
    loaded.publish(await SqlActiveCategories(sessions).active_ids(), NOW)
    version = await repo.save(loaded, 1, user)
    subject = f"sub-{uuid4()}"
    await SqlUserRepository(sessions).get_or_create(subject, "", "")
    assert await SqlFavoriteRepository(sessions, TEST_URLS).add(subject, event.id)
    loaded.delete()
    await repo.save(loaded, version, user)

    received: list[OutboxMessage] = []

    class Queue:
        async def enqueue_domain_event(self, message: OutboxMessage) -> None:
            received.append(message)

    outbox = SqlOutboxStore(sessions)
    assert await RelayOutbox(outbox, Queue())() == 2
    assert await RelayOutbox(outbox, Queue())() == 0

    async def ignore(*_args: object) -> None:
        return None

    handle = HandleDomainEvent(cache, SqlEventFavorites(sessions), ignore, ignore)
    for message in received:
        await handle(message)
    try:
        assert [m.type for m in received] == ["event.published", "event.deleted"]
        assert await cache.generation("catalog") == 2
        async with sessions() as session:
            remaining = await session.scalar(
                select(func.count())
                .select_from(FavoriteRow)
                .where(FavoriteRow.event_id == event.id)
            )
        assert remaining == 0
        assert await repo.get(event.id) is None  # soft-deleted
    finally:
        await client.aclose()


async def test_purge_removes_old_dispatched_messages_only(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    old, recent, pending = uuid4(), uuid4(), uuid4()
    async with sessions.begin() as session:
        session.add_all(
            [
                OutboxRow(
                    id=old, type="event.updated", payload={}, dispatched_at=NOW - timedelta(days=15)
                ),
                OutboxRow(
                    id=recent,
                    type="event.updated",
                    payload={},
                    dispatched_at=NOW - timedelta(days=13),
                ),
                OutboxRow(id=pending, type="event.updated", payload={}),
            ]
        )
    await PurgeOutbox(SqlOutboxStore(sessions), now=lambda: NOW)()
    async with sessions() as session:
        ids = set(
            (
                await session.scalars(
                    select(OutboxRow.id).where(OutboxRow.id.in_([old, recent, pending]))
                )
            ).all()
        )
    assert ids == {recent, pending}
