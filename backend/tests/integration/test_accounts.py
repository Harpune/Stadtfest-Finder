"""SqlUserRepository and SqlRegionDirectory against PostgreSQL."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlRegionDirectory, SqlUserRepository
from stadtfest.adapters.outbound.persistence.models import AppUserRow, EventRow
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), date(2026, 9, 25))
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="module")
def users(sessions: async_sessionmaker[AsyncSession]) -> SqlUserRepository:
    return SqlUserRepository(sessions)


async def test_get_or_create_is_idempotent_and_race_safe(users: SqlUserRepository) -> None:
    subject = f"sub-{uuid4()}"
    results = await asyncio.gather(
        *(users.get_or_create(subject, "Lena", "Beispiel") for _ in range(5))
    )
    assert len({record.id for record in results}) == 1
    again = await users.get_or_create(subject, "Other", "Name")
    assert (again.first_name, again.last_name) == ("Lena", "Beispiel")


async def test_update_name(users: SqlUserRepository) -> None:
    subject = f"sub-{uuid4()}"
    assert await users.update_name(subject, "A", "B") is None
    created = await users.get_or_create(subject, "", "")
    updated = await users.update_name(subject, "Mia", "Muster")
    assert updated is not None
    assert (updated.id, updated.first_name, updated.last_name) == (created.id, "Mia", "Muster")


async def test_delete_personal_data_removes_user_and_audit_references(
    users: SqlUserRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    subject = f"sub-{uuid4()}"
    user = await users.get_or_create(subject, "Mia", "Moderatorin")
    async with sessions.begin() as session:
        event_id = await session.scalar(select(EventRow.id).limit(1))
        await session.execute(
            update(EventRow)
            .where(EventRow.id == event_id)
            .values(created_by=user.id, updated_by=user.id)
        )

    assert await users.delete_personal_data(subject) is True
    assert await users.delete_personal_data(subject) is False

    async with sessions() as session:
        assert await session.get(AppUserRow, user.id) is None
        event = await session.get_one(EventRow, event_id)
        assert (event.created_by, event.updated_by) == (None, None)


async def test_region_lookup(sessions: async_sessionmaker[AsyncSession]) -> None:
    regions = SqlRegionDirectory(sessions)
    ostalb = await regions.get_by_key("ostalb")
    assert ostalb is not None
    assert ostalb.key == "ostalb"
    assert await regions.get_by_key("nowhere") is None
