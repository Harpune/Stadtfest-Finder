"""Category maintenance against PostgreSQL and Redis (R09)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.cache.redis_cache import RedisCache
from stadtfest.adapters.outbound.persistence.catalog import SqlCatalog
from stadtfest.adapters.outbound.persistence.categories import SqlCategoryRepository
from stadtfest.adapters.outbound.persistence.models import EventRow, OutboxRow
from stadtfest.adapters.outbound.persistence.outbox import SqlEventFavorites, SqlOutboxStore
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.events.use_cases import ListActiveCategories
from stadtfest.application.moderation.categories import (
    CategoryInUseError,
    DuplicateCategoryNameError,
)
from stadtfest.application.outbox.ports import OutboxMessage
from stadtfest.application.outbox.use_cases import HandleDomainEvent, RelayOutbox
from stadtfest.domain.events.category import CategoryDraft
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

TODAY = date(2026, 9, 25)


@pytest.fixture
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    # Function scope: these tests delete seed categories, so every test reloads the seed.
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), TODAY)
    yield engine
    await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def repo(sessions: async_sessionmaker[AsyncSession]) -> SqlCategoryRepository:
    return SqlCategoryRepository(sessions)


async def _events_with(sessions: async_sessionmaker[AsyncSession], category_id: object) -> int:
    async with sessions() as session:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(EventRow)
                .where(EventRow.category_id == category_id)
            )
            or 0
        )


async def test_list_counts_events_except_deleted(
    repo: SqlCategoryRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    before = {c.id: c.event_count for c in await repo.list_all()}
    category_id, count = next((k, v) for k, v in before.items() if v > 0)
    async with sessions.begin() as session:
        victim = await session.scalar(
            select(EventRow.id).where(EventRow.category_id == category_id).limit(1)
        )
        await session.execute(
            update(EventRow).where(EventRow.id == victim).values(deleted_at=datetime.now(UTC))
        )

    after = await repo.get(category_id)

    assert after is not None
    assert after.event_count == count - 1


async def test_add_appends_and_rejects_duplicate_names(repo: SqlCategoryRepository) -> None:
    last = max(c.sort_order for c in await repo.list_all())

    created = await repo.add(uuid4(), CategoryDraft("Testkategorie", "🍷", "#C792EA"))

    assert (created.sort_order, created.event_count) == (last + 1, 0)
    with pytest.raises(DuplicateCategoryNameError):
        await repo.add(uuid4(), CategoryDraft("TESTKATEGORIE", "🍷", "#C792EA"))
    first = (await repo.list_all())[0]
    with pytest.raises(DuplicateCategoryNameError):
        await repo.update(created.id, CategoryDraft(first.name.lower(), "🍷", "#C792EA"))


async def test_reorder(repo: SqlCategoryRepository) -> None:
    ids = [c.id for c in await repo.list_all()]

    await repo.reorder(list(reversed(ids)))

    assert [c.id for c in await repo.list_all()] == list(reversed(ids))


async def test_delete_moves_all_events_including_deleted_ones(
    repo: SqlCategoryRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    categories = await repo.list_all()
    source = next(c for c in categories if c.event_count > 0)
    target = next(c for c in categories if c.id != source.id)
    async with sessions.begin() as session:
        await session.execute(
            update(EventRow)
            .where(
                EventRow.id.in_(
                    select(EventRow.id).where(EventRow.category_id == source.id).limit(1)
                )
            )
            .values(deleted_at=datetime.now(UTC))
        )
    total = await _events_with(sessions, source.id)
    target_before = await _events_with(sessions, target.id)

    with pytest.raises(CategoryInUseError):
        await repo.delete(source.id, None)
    moved = await repo.delete(source.id, target.id)

    assert moved == source.event_count - 1  # deleted events move too, but are not reported
    assert await repo.get(source.id) is None
    assert await _events_with(sessions, target.id) == target_before + total


async def test_failed_move_changes_nothing(
    repo: SqlCategoryRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    source = next(c for c in await repo.list_all() if c.event_count > 0)
    count = await _events_with(sessions, source.id)

    # An unknown replacement violates the foreign key while moving: the transaction rolls back.
    with pytest.raises(IntegrityError):
        await repo.delete(source.id, uuid4())

    assert await repo.get(source.id) is not None
    assert await _events_with(sessions, source.id) == count


async def test_changes_give_the_public_list_a_new_etag(
    repo: SqlCategoryRepository, sessions: async_sessionmaker[AsyncSession], redis_url: str
) -> None:
    redis = Redis.from_url(redis_url)
    cache = RedisCache(redis)
    list_active = ListActiveCategories(SqlCatalog(sessions, ImageUrls("https://img.test/b")), cache)
    async with sessions.begin() as session:
        await session.execute(
            update(OutboxRow)
            .where(OutboxRow.dispatched_at.is_(None))
            .values(dispatched_at=datetime.now(UTC))
        )
    before = await list_active()
    target = before.categories[0]

    await repo.update(target.id, CategoryDraft(target.name, target.emoji, target.color, False))
    received: list[OutboxMessage] = []

    class Queue:
        async def enqueue_domain_event(self, message: OutboxMessage) -> None:
            received.append(message)

    async def ignore(*_args: object) -> None:
        return None

    await RelayOutbox(SqlOutboxStore(sessions), Queue())()
    handle = HandleDomainEvent(cache, SqlEventFavorites(sessions), ignore, ignore)
    for message in received:
        await handle(message)
    after = await list_active()
    await redis.aclose()

    assert [m.type for m in received] == ["category.changed"]
    assert after.etag != before.etag
    assert target.id not in {c.id for c in after.categories}
