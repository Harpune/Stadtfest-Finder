"""Invitation repository against PostgreSQL (R14)."""

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
from stadtfest.adapters.outbound.persistence.favorites import SqlFavoriteRepository
from stadtfest.adapters.outbound.persistence.invitations import SqlInvitationRepository
from stadtfest.adapters.outbound.persistence.models import (
    EventRow,
    InvitationRow,
    OutboxRow,
)
from stadtfest.adapters.outbound.persistence.notifications import (
    SqlNotificationStore,
    SqlRecipients,
)
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.domain.collections.invitations import InviteeStatus
from stadtfest.domain.notifications.notification import InvitationFacts, NotificationType
from tests.integration.seed_support import load

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
URLS = ImageUrls("https://img.test/x")


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
def invitations(sessions: async_sessionmaker[AsyncSession]) -> SqlInvitationRepository:
    return SqlInvitationRepository(sessions, URLS)


async def _user(sessions: async_sessionmaker[AsyncSession], first: str) -> tuple[str, UUID]:
    subject = f"sub-{uuid4()}"
    record = await SqlUserRepository(sessions).get_or_create(subject, first, "Test")
    return subject, record.id


async def _event(sessions: async_sessionmaker[AsyncSession]) -> UUID:
    async with sessions() as session:
        found = await session.scalar(
            select(EventRow.id)
            .where(EventRow.status == "published", EventRow.deleted_at.is_(None))
            .order_by(EventRow.start_date.desc())
            .limit(1)
        )
    assert found is not None
    return found


async def _outbox(sessions: async_sessionmaker[AsyncSession], invitation: UUID) -> list[str]:
    async with sessions() as session:
        rows = await session.scalars(
            select(OutboxRow.type)
            .where(OutboxRow.payload["invitationId"].astext == str(invitation))
            .order_by(OutboxRow.type)
        )
        return list(rows)


async def test_invite_link_respond_and_remind(
    sessions: async_sessionmaker[AsyncSession], invitations: SqlInvitationRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    tim_subject, tim = await _user(sessions, "Tim")
    _, mia = await _user(sessions, "Mia")
    event = await _event(sessions)

    first = await invitations.invite(event, lena, [tim], "Kommst du mit?", NOW)
    again = await invitations.invite(event, lena, [tim, mia], None, NOW + timedelta(minutes=1))
    assert first == again
    view = await invitations.of_host(event, lena)
    assert view is not None
    assert view.message == "Kommst du mit?"
    assert [i.person.first_name for i in view.invitees] == ["Tim", "Mia"]
    assert view.event.id == event

    token = await invitations.link_token(event, lena, "A" * 22, NOW)
    assert await invitations.link_token(event, lena, "B" * 22, NOW) == token
    by_token = await invitations.by_token(token)
    assert by_token is not None
    assert by_token.id == first

    await invitations.respond(first, tim, InviteeStatus.ACCEPTED, NOW)
    await invitations.respond(first, tim, InviteeStatus.ACCEPTED, NOW)  # unchanged: no event
    assert await SqlFavoriteRepository(sessions, URLS).is_favorite(tim_subject, event)
    accepted = await invitations.accepted_for(event, tim)
    assert accepted is not None
    assert accepted.id == first
    assert await SqlRecipients(sessions).accepted_invitees(event) == [tim]

    assert await invitations.remind(first, NOW) == 1  # Mia is still open
    assert await invitations.remind(first, NOW + timedelta(hours=1)) == 0  # within 24 h
    assert [r.id for r in await invitations.received_by(mia)] == [first]
    assert await _outbox(sessions, first) == [
        "invitation.invitees_added",
        "invitation.invitees_added",
        "invitation.reminded",
        "invitation.responded",
    ]


async def test_invitation_notifications_name_actor_and_event(
    sessions: async_sessionmaker[AsyncSession], invitations: SqlInvitationRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    _, tim = await _user(sessions, "Tim")
    event = await _event(sessions)
    invitation = await invitations.invite(event, lena, [tim], None, NOW)
    store = SqlNotificationStore(sessions)

    [added] = await store.add(
        [tim], NotificationType.INVITE, invitation, f"i:{invitation}", NOW, actor_id=lena
    )
    [entry] = await store.page(tim, None, 10)
    assert isinstance(entry.facts, InvitationFacts)
    assert (entry.facts.event_id, entry.facts.actor_first_name) == (event, "Lena")
    assert entry.notification.subject_id == invitation
    [pending] = await store.unpushed([added])
    assert pending.facts == entry.facts


async def test_purge_and_account_deletion(
    sessions: async_sessionmaker[AsyncSession], invitations: SqlInvitationRepository
) -> None:
    lena_subject, lena = await _user(sessions, "Lena")
    _, tim = await _user(sessions, "Tim")
    event = await _event(sessions)
    invitation = await invitations.invite(event, lena, [tim], None, NOW)
    await SqlNotificationStore(sessions).add(
        [tim], NotificationType.INVITE, invitation, f"i:{invitation}", NOW, actor_id=lena
    )
    async with sessions() as session:
        end = await session.scalar(select(EventRow.end_date).where(EventRow.id == event))
    assert end is not None
    cutoff = datetime.combine(end, datetime.min.time(), UTC)
    assert await invitations.purge(cutoff) == 0  # ended on that day, not before

    assert await SqlUserRepository(sessions).delete_personal_data(lena_subject)
    assert await invitations.get(invitation) is None
    assert await invitations.received_by(tim) == []
    assert await SqlNotificationStore(sessions).page(tim, None, 10) == []


async def test_purge_deletes_invitations_of_long_ended_events(
    sessions: async_sessionmaker[AsyncSession], invitations: SqlInvitationRepository
) -> None:
    _, lena = await _user(sessions, "Lena")
    event = await _event(sessions)
    invitation = await invitations.invite(event, lena, [], None, NOW)
    async with sessions.begin() as session:
        end = await session.scalar(select(EventRow.end_date).where(EventRow.id == event))
        assert end is not None
        await session.execute(update(EventRow).where(EventRow.id == event).values(end_date=end))
    later = datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC)
    assert await invitations.purge(later) >= 1
    async with sessions() as session:
        left = await session.scalar(
            select(func.count()).select_from(InvitationRow).where(InvitationRow.id == invitation)
        )
    assert left == 0
