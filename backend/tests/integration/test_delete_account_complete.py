"""Test suite "DeleteAccount vollständig" (R16-US7, Löschkonzept).

A user with data in every context is deleted through the `DeleteAccount` use case. Then a
schema scan over every table and every text-like column of the database (taken from
`information_schema`, so new tables are covered automatically) must not find the user's ID
or IdP subject anywhere.

The fixture must reach every column with a foreign key to `app_user`: a new table that
references users fails `test_fixture_covers_every_user_reference` until it is added here
and to `SqlUserRepository.delete_personal_data` / the Löschkonzept.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stadtfest.adapters.outbound.persistence.accounts import SqlUserRepository
from stadtfest.adapters.outbound.persistence.friends import SqlFriendRepository
from stadtfest.adapters.outbound.persistence.models import (
    AiSearchJobRow,
    DeviceRow,
    EventRow,
    FavoriteRow,
    InvitationRow,
    InviteeRow,
    ListEventRow,
    ListMemberRow,
    NotificationRow,
    NotificationSettingsRow,
    SharedListRow,
    UploadRow,
)
from stadtfest.application.identity.use_cases import DeleteAccount
from stadtfest.domain.identity.principal import Principal, Role
from tests.fakes import FakeAccountJobs, FakeDeletedAccounts, FakeIdpAdmin
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

# Column types that can hold a user ID or subject, also inside JSON or arrays.
_SCANNED_TYPES = ("uuid", "text", "character varying", "jsonb", "json", "ARRAY")


@dataclass(frozen=True)
class Column:
    """A scanned column."""

    table: str
    column: str


@pytest.fixture(scope="module")
async def engine(migrated_postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_url)
    await load(async_sessionmaker(engine), date(2026, 9, 25))
    yield engine
    await engine.dispose()


@pytest.fixture(scope="module")
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _scanned_columns(session: AsyncSession) -> list[Column]:
    rows = await session.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name <> 'alembic_version' "
            "AND data_type = ANY(:types) ORDER BY table_name, column_name"
        ),
        {"types": list(_SCANNED_TYPES)},
    )
    return [Column(table, column) for table, column in rows]


async def _user_references(session: AsyncSession) -> set[Column]:
    """Every column with a foreign key to `app_user.id`."""
    rows = await session.execute(
        text(
            "SELECT kcu.table_name, kcu.column_name "
            "FROM information_schema.referential_constraints rc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON kcu.constraint_name = rc.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON ccu.constraint_name = rc.unique_constraint_name "
            "WHERE ccu.table_name = 'app_user' AND ccu.column_name = 'id'"
        )
    )
    return {Column(table, column) for table, column in rows}


async def _columns_containing(
    sessions: async_sessionmaker[AsyncSession], needles: list[str]
) -> set[Column]:
    """Columns in which any row contains one of the needles (as text)."""
    found: set[Column] = set()
    async with sessions() as session:
        for column in await _scanned_columns(session):
            for needle in needles:
                hit = await session.scalar(
                    text(
                        f'SELECT EXISTS (SELECT 1 FROM "{column.table}" '  # noqa: S608  # names from information_schema
                        f'WHERE position(:needle IN "{column.column}"::text) > 0)'
                    ),
                    {"needle": needle},
                )
                if hit:
                    found.add(column)
    return found


@dataclass(frozen=True)
class Account:
    """The user to delete and a friend who keeps their account."""

    user_id: UUID
    subject: str
    friend_id: UUID
    shared_list_id: UUID
    own_list_id: UUID


async def _user_with_data_everywhere(sessions: async_sessionmaker[AsyncSession]) -> Account:
    users = SqlUserRepository(sessions)
    subject = f"sub-delete-{uuid4()}"
    user = await users.get_or_create(subject, "Mia", "Moderatorin")
    friend = await users.get_or_create(f"sub-friend-{uuid4()}", "Finn", "Freund")
    # Friend link and friendship through the repository, so the outbox event exists too.
    friends = SqlFriendRepository(sessions)
    now = datetime.now(UTC)
    await friends.set_link(user.id, f"link-{uuid4().hex}", now)
    await friends.befriend(user.id, friend.id, now)
    shared_list_id, own_list_id = uuid4(), uuid4()
    own_invitation_id, received_invitation_id = uuid4(), uuid4()

    async with sessions.begin() as session:
        event_id = await session.scalar(select(EventRow.id).order_by(EventRow.id).limit(1))
        assert event_id is not None
        await session.execute(
            update(EventRow)
            .where(EventRow.id == event_id)
            .values(created_by=user.id, updated_by=user.id)
        )
        session.add_all(
            [
                FavoriteRow(user_id=user.id, event_id=event_id),
                UploadRow(id=uuid4(), user_id=user.id, content_type="image/jpeg", size_bytes=1),
                AiSearchJobRow(id=uuid4(), moderator_id=user.id, postal_code="73430"),
                NotificationSettingsRow(
                    user_id=user.id,
                    remind=True,
                    remind_days_before=1,
                    near=True,
                    home_postal_code="73430",
                    home_place_name="Aalen",
                    home_location="SRID=4326;POINT(10.09 48.84)",
                    near_radius_km=25,
                    change=True,
                    invite=True,
                    rsvp=True,
                ),
                DeviceRow(
                    token=f"push-{uuid4()}", user_id=user.id, platform="ios", provider="direct"
                ),
                SharedListRow(id=shared_list_id, name="Sommer", created_by=user.id),
                SharedListRow(id=own_list_id, name="Nur ich", created_by=user.id),
            ]
        )
        await session.flush()
        session.add_all(
            [
                ListMemberRow(list_id=shared_list_id, user_id=user.id, added_by=user.id),
                ListMemberRow(list_id=shared_list_id, user_id=friend.id, added_by=user.id),
                ListMemberRow(list_id=own_list_id, user_id=user.id, added_by=user.id),
                ListEventRow(list_id=shared_list_id, event_id=event_id, added_by=user.id),
                InvitationRow(
                    id=own_invitation_id, event_id=event_id, host_id=user.id, message="Kommst du?"
                ),
                InvitationRow(id=received_invitation_id, event_id=event_id, host_id=friend.id),
            ]
        )
        await session.flush()
        session.add_all(
            [
                InviteeRow(invitation_id=own_invitation_id, user_id=friend.id),
                InviteeRow(invitation_id=received_invitation_id, user_id=user.id),
                NotificationRow(
                    id=uuid4(),
                    user_id=user.id,
                    type="reminder",
                    event_id=event_id,
                    dedupe_key=f"reminder:{event_id}:{uuid4()}",
                ),
                NotificationRow(
                    id=uuid4(),
                    user_id=friend.id,
                    type="friend_added",
                    actor_user_id=user.id,
                    dedupe_key=f"friend_added:{uuid4()}",
                ),
            ]
        )
    return Account(user.id, subject, friend.id, shared_list_id, own_list_id)


@pytest.fixture
async def account(sessions: async_sessionmaker[AsyncSession]) -> Account:
    return await _user_with_data_everywhere(sessions)


def _delete_account(sessions: async_sessionmaker[AsyncSession]) -> DeleteAccount:
    return DeleteAccount(
        SqlUserRepository(sessions),
        FakeIdpAdmin(),
        FakeAccountJobs(),
        FakeDeletedAccounts(),
        token_leeway_seconds=30,
    )


async def test_fixture_covers_every_user_reference(
    sessions: async_sessionmaker[AsyncSession], account: Account
) -> None:
    async with sessions() as session:
        references = await _user_references(session)
    found = await _columns_containing(sessions, [str(account.user_id)])

    assert references, "no foreign keys to app_user found"
    missing = references - found
    assert missing == set(), f"extend the fixture (and the Löschkonzept) for {missing}"


async def test_schema_scan_finds_nothing_after_delete_account(
    sessions: async_sessionmaker[AsyncSession], account: Account
) -> None:
    needles = [str(account.user_id), account.subject]
    assert await _columns_containing(sessions, needles)  # the scan sees the data before

    await _delete_account(sessions)(Principal(account.subject, frozenset({Role.USER})))

    assert await _columns_containing(sessions, needles) == set()


async def test_data_of_other_users_survives(
    sessions: async_sessionmaker[AsyncSession], account: Account
) -> None:
    await _delete_account(sessions)(Principal(account.subject, frozenset({Role.USER})))

    async with sessions() as session:
        members = (
            await session.scalars(
                select(ListMemberRow.user_id).where(ListMemberRow.list_id == account.shared_list_id)
            )
        ).all()
        own_list = await session.get(SharedListRow, account.own_list_id)
        shared_list = await session.get(SharedListRow, account.shared_list_id)

    assert members == [account.friend_id]
    assert shared_list is not None
    assert shared_list.created_by is None
    assert own_list is None  # nobody left in it
    assert await _columns_containing(sessions, [str(account.friend_id)])
