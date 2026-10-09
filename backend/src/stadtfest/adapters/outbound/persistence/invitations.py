"""PostgreSQL implementation of the invitation repository (R14)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import ColumnElement, cast, delete, func, or_, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql import Select

from stadtfest.adapters.outbound.persistence.covers import cover_lateral, cover_view
from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    EventRow,
    FavoriteRow,
    InvitationRow,
    InviteeRow,
    OutboxRow,
)
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.collections.invitations import (
    InvitationPersonView,
    InvitationView,
    InviteeView,
)
from stadtfest.application.events.views import EventSummaryView
from stadtfest.domain.collections.invitations import (
    REMINDER_INTERVAL,
    InvitationEventType,
    InviteeStatus,
)
from stadtfest.domain.events.event import PUBLIC_STATUSES, EventStatus
from stadtfest.domain.events.geo import GeoPoint

_PUBLIC = sorted(status.value for status in PUBLIC_STATUSES)


def _visible() -> list[ColumnElement[bool]]:
    return [EventRow.status.in_(_PUBLIC), EventRow.deleted_at.is_(None)]


def _event_query() -> Select[*tuple[Any, ...]]:  # Any: long row type, read via `_summary`
    """Publicly visible events with cover, as `EventSummaryView` columns."""
    cover = cover_lateral()
    return (
        select(
            EventRow.id,
            EventRow.name,
            EventRow.short_name,
            EventRow.status,
            EventRow.start_date,
            EventRow.end_date,
            EventRow.place,
            EventRow.city,
            EventRow.category_id,
            func.ST_Y(cast(EventRow.location, Geometry)).label("lat"),
            func.ST_X(cast(EventRow.location, Geometry)).label("lon"),
            cover.c.id.label("cover_id"),
            cover.c.width.label("cover_width"),
            cover.c.height.label("cover_height"),
        )
        .outerjoin_from(EventRow, cover, true())
        .where(*_visible())
    )


def _summary(row: Any, urls: ImageUrls) -> EventSummaryView:  # noqa: ANN401  # SQLAlchemy Row
    return EventSummaryView(
        id=row.id,
        name=row.name,
        short_name=row.short_name,
        status=EventStatus(row.status),
        start_date=row.start_date,
        end_date=row.end_date,
        place=row.place,
        city=row.city,
        location=GeoPoint(row.lat, row.lon),
        category_id=row.category_id,
        cover_image=cover_view(row, urls),
    )


def _outbox(event_type: InvitationEventType, payload: dict[str, object]) -> dict[str, object]:
    """An outbox row; payloads carry IDs only, never the message."""
    return {"id": uuid.uuid4(), "type": event_type.value, "payload": payload}


class SqlInvitationRepository:
    """Tables `invitation` and `invitee`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], image_urls: ImageUrls) -> None:
        """Create the repository."""
        self._sessions = sessions
        self._urls = image_urls

    async def event(self, event_id: UUID) -> EventSummaryView | None:
        """The publicly visible event."""
        async with self._sessions() as session:
            rows = (await session.execute(_event_query().where(EventRow.id == event_id))).all()
        return _summary(rows[0], self._urls) if rows else None

    async def get(self, invitation_id: UUID) -> InvitationView | None:
        """One invitation of a visible event."""
        async with self._sessions() as session:
            views = await self._views(session, InvitationRow.id == invitation_id)
        return views[0] if views else None

    async def of_host(self, event_id: UUID, host_id: UUID) -> InvitationView | None:
        """The host's invitation to the event."""
        async with self._sessions() as session:
            views = await self._views(
                session, InvitationRow.event_id == event_id, InvitationRow.host_id == host_id
            )
        return views[0] if views else None

    async def accepted_for(self, event_id: UUID, user_id: UUID) -> InvitationView | None:
        """The oldest invitation to the event that the user accepted."""
        accepted = select(InviteeRow.invitation_id).where(
            InviteeRow.user_id == user_id,
            InviteeRow.status == InviteeStatus.ACCEPTED.value,
        )
        async with self._sessions() as session:
            views = await self._views(
                session, InvitationRow.event_id == event_id, InvitationRow.id.in_(accepted)
            )
        return min(views, key=lambda v: (v.created_at, v.id), default=None)

    async def received_by(self, user_id: UUID) -> list[InvitationView]:
        """Received invitations, newest first."""
        received = select(InviteeRow.invitation_id).where(InviteeRow.user_id == user_id)
        async with self._sessions() as session:
            views = await self._views(session, InvitationRow.id.in_(received))
        return sorted(views, key=lambda v: (v.created_at, v.id), reverse=True)

    async def by_token(self, token: str) -> InvitationView | None:
        """The invitation with this link token."""
        async with self._sessions() as session:
            views = await self._views(session, InvitationRow.link_token == token)
        return views[0] if views else None

    async def invite(
        self,
        event_id: UUID,
        host_id: UUID,
        user_ids: Sequence[UUID],
        message: str | None,
        now: datetime,
    ) -> UUID:
        """Invitation, new invitees, message and `invitation.invitees_added` in one transaction."""
        async with self._sessions.begin() as session:
            invitation_id = await self._ensure(session, event_id, host_id, now)
            if message is not None:
                await session.execute(
                    update(InvitationRow)
                    .where(InvitationRow.id == invitation_id)
                    .values(message=message)
                )
            if user_ids:
                added = list(
                    await session.scalars(
                        insert(InviteeRow)
                        .values(
                            [
                                {
                                    "invitation_id": invitation_id,
                                    "user_id": user_id,
                                    "status": InviteeStatus.OPEN.value,
                                    "invited_at": now,
                                }
                                for user_id in user_ids
                            ]
                        )
                        .on_conflict_do_nothing()
                        .returning(InviteeRow.user_id)
                    )
                )
                if added:
                    await session.execute(
                        insert(OutboxRow).values(
                            **_outbox(
                                InvitationEventType.INVITEES_ADDED,
                                {
                                    "invitationId": str(invitation_id),
                                    "hostId": str(host_id),
                                    "userIds": [str(user) for user in added],
                                },
                            )
                        )
                    )
        return invitation_id

    async def link_token(self, event_id: UUID, host_id: UUID, token: str, now: datetime) -> str:
        """Keep an existing token, otherwise store the new one."""
        async with self._sessions.begin() as session:
            invitation_id = await self._ensure(session, event_id, host_id, now)
            await session.execute(
                update(InvitationRow)
                .where(InvitationRow.id == invitation_id, InvitationRow.link_token.is_(None))
                .values(link_token=token)
            )
            stored = await session.scalar(
                select(InvitationRow.link_token).where(InvitationRow.id == invitation_id)
            )
        assert stored is not None  # noqa: S101  # set just above
        return stored

    async def remind(self, invitation_id: UUID, now: datetime) -> int:
        """Set `last_reminder_at` unless set within 24 h, then write `invitation.reminded`."""
        async with self._sessions.begin() as session:
            host_id = await session.scalar(
                update(InvitationRow)
                .where(
                    InvitationRow.id == invitation_id,
                    or_(
                        InvitationRow.last_reminder_at.is_(None),
                        InvitationRow.last_reminder_at <= now - REMINDER_INTERVAL,
                    ),
                )
                .values(last_reminder_at=now)
                .returning(InvitationRow.host_id)
            )
            if host_id is None:
                return 0  # reminded concurrently
            open_ids = list(
                await session.scalars(
                    select(InviteeRow.user_id).where(
                        InviteeRow.invitation_id == invitation_id,
                        InviteeRow.status == InviteeStatus.OPEN.value,
                    )
                )
            )
            if open_ids:
                await session.execute(
                    insert(OutboxRow).values(
                        **_outbox(
                            InvitationEventType.REMINDED,
                            {
                                "invitationId": str(invitation_id),
                                "hostId": str(host_id),
                                "userIds": [str(user) for user in open_ids],
                            },
                        )
                    )
                )
        return len(open_ids)

    async def respond(
        self, invitation_id: UUID, user_id: UUID, status: InviteeStatus, now: datetime
    ) -> None:
        """Answer, favorite on `accepted` and `invitation.responded` in one transaction."""
        async with self._sessions.begin() as session:
            row = (
                await session.execute(
                    select(InviteeRow.status, InvitationRow.host_id, InvitationRow.event_id)
                    .join(InvitationRow, InvitationRow.id == InviteeRow.invitation_id)
                    .where(InviteeRow.invitation_id == invitation_id, InviteeRow.user_id == user_id)
                    .with_for_update(of=InviteeRow)
                )
            ).one_or_none()
            if row is None:
                return
            await session.execute(
                update(InviteeRow)
                .where(InviteeRow.invitation_id == invitation_id, InviteeRow.user_id == user_id)
                .values(
                    status=status.value,
                    responded_at=None if status is InviteeStatus.OPEN else now,
                )
            )
            if status is InviteeStatus.ACCEPTED:
                await self._favorite(session, user_id, row.event_id)
            if row.status != status.value and status is not InviteeStatus.OPEN:
                await session.execute(
                    insert(OutboxRow).values(
                        **_outbox(
                            InvitationEventType.RESPONDED,
                            {
                                "invitationId": str(invitation_id),
                                "hostId": str(row.host_id),
                                "userId": str(user_id),
                                "status": status.value,
                            },
                        )
                    )
                )

    async def join(self, invitation_id: UUID, user_id: UUID, now: datetime) -> None:
        """Add the user as open invitee once."""
        async with self._sessions.begin() as session:
            await session.execute(
                insert(InviteeRow)
                .values(
                    invitation_id=invitation_id,
                    user_id=user_id,
                    status=InviteeStatus.OPEN.value,
                    invited_at=now,
                )
                .on_conflict_do_nothing()
            )

    async def purge(self, ended_before: datetime) -> int:
        """Delete invitations whose event ended before the day of `ended_before`."""
        ended = select(EventRow.id).where(EventRow.end_date < ended_before.date())
        async with self._sessions.begin() as session:
            deleted = await session.scalars(
                delete(InvitationRow)
                .where(InvitationRow.event_id.in_(ended))
                .returning(InvitationRow.id)
            )
            return len(list(deleted))

    @staticmethod
    async def _ensure(session: AsyncSession, event_id: UUID, host_id: UUID, now: datetime) -> UUID:
        await session.execute(
            insert(InvitationRow)
            .values(id=uuid.uuid4(), event_id=event_id, host_id=host_id, created_at=now)
            .on_conflict_do_nothing(index_elements=[InvitationRow.event_id, InvitationRow.host_id])
        )
        found = await session.scalar(
            select(InvitationRow.id).where(
                InvitationRow.event_id == event_id, InvitationRow.host_id == host_id
            )
        )
        assert found is not None  # noqa: S101  # inserted just above
        return found

    @staticmethod
    async def _favorite(session: AsyncSession, user_id: UUID, event_id: UUID) -> None:
        """Add the favorite once and count it (same rule as the favorites repository)."""
        inserted = await session.scalar(
            insert(FavoriteRow)
            .values(user_id=user_id, event_id=event_id)
            .on_conflict_do_nothing()
            .returning(FavoriteRow.event_id)
        )
        if inserted is not None:
            await session.execute(
                update(EventRow)
                .where(EventRow.id == event_id)
                .values(favorite_count=EventRow.favorite_count + 1)
            )

    async def _views(
        self, session: AsyncSession, *conditions: ColumnElement[bool]
    ) -> list[InvitationView]:
        """Invitations of visible events matching the conditions, with host and invitees."""
        rows = (
            await session.execute(
                _event_query()
                .add_columns(
                    InvitationRow.id.label("invitation_id"),
                    InvitationRow.message,
                    InvitationRow.created_at,
                    InvitationRow.last_reminder_at,
                    AppUserRow.id.label("host_id"),
                    AppUserRow.first_name.label("host_first_name"),
                    AppUserRow.last_name.label("host_last_name"),
                )
                .join_from(EventRow, InvitationRow, InvitationRow.event_id == EventRow.id)
                .join_from(InvitationRow, AppUserRow, AppUserRow.id == InvitationRow.host_id)
                .where(*conditions)
            )
        ).all()
        if not rows:
            return []
        invitees = (
            await session.execute(
                select(
                    InviteeRow.invitation_id,
                    InviteeRow.status,
                    InviteeRow.invited_at,
                    InviteeRow.responded_at,
                    AppUserRow.id,
                    AppUserRow.first_name,
                    AppUserRow.last_name,
                )
                .join(AppUserRow, AppUserRow.id == InviteeRow.user_id)
                .where(InviteeRow.invitation_id.in_([row.invitation_id for row in rows]))
                .order_by(InviteeRow.invited_at, AppUserRow.first_name, AppUserRow.id)
            )
        ).all()
        by_invitation: dict[UUID, list[InviteeView]] = {}
        for invitee in invitees:
            by_invitation.setdefault(invitee.invitation_id, []).append(
                InviteeView(
                    person=InvitationPersonView(invitee.id, invitee.first_name, invitee.last_name),
                    status=InviteeStatus(invitee.status),
                    invited_at=invitee.invited_at,
                    responded_at=invitee.responded_at,
                )
            )
        return [
            InvitationView(
                id=row.invitation_id,
                event=_summary(row, self._urls),
                host=InvitationPersonView(row.host_id, row.host_first_name, row.host_last_name),
                message=row.message,
                created_at=row.created_at,
                last_reminder_at=row.last_reminder_at,
                invitees=by_invitation.get(row.invitation_id, []),
            )
            for row in rows
        ]
