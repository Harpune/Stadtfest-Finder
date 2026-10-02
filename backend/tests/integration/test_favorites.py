"""SqlFavoriteRepository against PostgreSQL (counters, visibility, cascade on account deletion)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.models import EventRow, FavoriteRow
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from tests.integration.seed_support import load

TEST_URLS = ImageUrls("https://img.test/stadtfest-images")

pytestmark = pytest.mark.integration

TODAY = date(2026, 9, 25)


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
def favorites(sessions: async_sessionmaker[AsyncSession]) -> SqlFavoriteRepository:
    return SqlFavoriteRepository(sessions, TEST_URLS)


@pytest.fixture(scope="module")
def users(sessions: async_sessionmaker[AsyncSession]) -> SqlUserRepository:
    return SqlUserRepository(sessions)


async def _event(sessions: async_sessionmaker[AsyncSession], *where: ColumnElement[bool]) -> UUID:
    async with sessions() as session:
        event_id: UUID | None = await session.scalar(
            select(EventRow.id).where(EventRow.deleted_at.is_(None), *where).limit(1)
        )
    assert event_id is not None
    return event_id


async def _count(sessions: async_sessionmaker[AsyncSession], event_id: UUID) -> int:
    async with sessions() as session:
        return (
            await session.scalar(select(EventRow.favorite_count).where(EventRow.id == event_id))
            or 0
        )


async def _user(users: SqlUserRepository) -> str:
    subject = f"sub-{uuid4()}"
    await users.get_or_create(subject, "Lena", "Beispiel")
    return subject


async def test_parallel_puts_count_every_user_once(
    favorites: SqlFavoriteRepository,
    users: SqlUserRepository,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    event_id = await _event(sessions, EventRow.status == "published")
    before = await _count(sessions, event_id)
    subjects = [await _user(users) for _ in range(5)]

    # Every user twice, all at the same time.
    results = await asyncio.gather(
        *(favorites.add(subject, event_id) for subject in subjects for _ in range(2))
    )

    assert all(results)
    assert await _count(sessions, event_id) == before + 5
    await asyncio.gather(*(favorites.remove(subject, event_id) for subject in subjects * 2))
    assert await _count(sessions, event_id) == before


async def test_drafts_and_unknown_events_cannot_be_added(
    favorites: SqlFavoriteRepository,
    users: SqlUserRepository,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    subject = await _user(users)
    draft = await _event(sessions, EventRow.status == "draft")
    assert await favorites.add(subject, draft) is False
    assert await favorites.add(subject, uuid4()) is False
    assert await favorites.list_for(subject, from_day=None) == []


async def test_list_orders_by_start_and_hides_past_on_request(
    favorites: SqlFavoriteRepository,
    users: SqlUserRepository,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    subject = await _user(users)
    past = await _event(sessions, EventRow.status == "published", EventRow.end_date < TODAY)
    upcoming = await _event(sessions, EventRow.status == "published", EventRow.end_date >= TODAY)
    for event_id in (upcoming, past):
        assert await favorites.add(subject, event_id)

    everything = await favorites.list_for(subject, from_day=None)
    current = await favorites.list_for(subject, from_day=TODAY)

    assert [f.event.id for f in everything] == [past, upcoming]
    assert [f.event.id for f in current] == [upcoming]
    assert everything[0].category_name
    assert everything[0].emoji
    assert await favorites.is_favorite(subject, past)
    assert not await favorites.is_favorite(f"sub-{uuid4()}", past)


async def test_account_deletion_removes_favorites_and_counts_down(
    favorites: SqlFavoriteRepository,
    users: SqlUserRepository,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    subject = f"sub-{uuid4()}"
    user = await users.get_or_create(subject, "Lena", "Beispiel")
    event_id = await _event(sessions, EventRow.status == "published")
    before = await _count(sessions, event_id)
    await favorites.add(subject, event_id)

    assert await users.delete_personal_data(subject)

    assert await _count(sessions, event_id) == before
    async with sessions() as session:
        remaining = await session.scalar(
            select(FavoriteRow.event_id).where(FavoriteRow.user_id == user.id).limit(1)
        )
    assert remaining is None
