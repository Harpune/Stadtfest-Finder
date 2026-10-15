"""PostgreSQL implementation of the notification ports (R11)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    ColumnElement,
    Integer,
    and_,
    cast,
    delete,
    func,
    or_,
    select,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

from stadtfest.adapters.outbound.persistence.models import (
    AiSearchJobRow,
    AppUserRow,
    DeviceRow,
    EventRow,
    FavoriteRow,
    InvitationRow,
    InviteeRow,
    NotificationRow,
    NotificationSettingsRow,
    SharedListRow,
)
from stadtfest.application.notifications.ports import (
    Device,
    DevicePlatform,
    ListedNotification,
    PageCursor,
    PushProvider,
    StoredNotification,
)
from stadtfest.domain.collections.invitations import InviteeStatus
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.notifications.notification import (
    EventFacts,
    Facts,
    InvitationFacts,
    ListFacts,
    NotificationType,
    PersonFacts,
    SubjectKind,
)
from stadtfest.domain.notifications.settings import Home, NotificationSettings

_DEFAULTS = NotificationSettings()


def _stored(row: NotificationRow) -> StoredNotification:
    notification_type = NotificationType(row.type)
    subject = {
        SubjectKind.EVENT: row.event_id,
        SubjectKind.PERSON: row.actor_user_id,
        SubjectKind.LIST: row.list_id,
        SubjectKind.INVITATION: row.invitation_id,
    }[notification_type.subject]
    assert subject is not None  # noqa: S101  # every type has its subject column set
    return StoredNotification(
        id=row.id,
        user_id=row.user_id,
        type=notification_type,
        subject_id=subject,
        read=row.read,
        created_at=row.created_at,
    )


_Actor = aliased(AppUserRow)
_InvitedEvent = aliased(EventRow)


def _visible() -> ColumnElement[bool]:
    """Notifications of deleted events are hidden (R11-US1); person ones always show."""
    return or_(NotificationRow.event_id.is_(None), EventRow.deleted_at.is_(None))


def _live_event() -> ColumnElement[bool]:
    """Events that were not deleted (recipients of event notifications)."""
    return EventRow.deleted_at.is_(None)


def _with_subjects[*Ts](query: Select[*Ts]) -> Select[*Ts]:
    return (
        query.outerjoin(EventRow, EventRow.id == NotificationRow.event_id)
        .outerjoin(_Actor, _Actor.id == NotificationRow.actor_user_id)
        .outerjoin(SharedListRow, SharedListRow.id == NotificationRow.list_id)
        .outerjoin(InvitationRow, InvitationRow.id == NotificationRow.invitation_id)
        .outerjoin(_InvitedEvent, _InvitedEvent.id == InvitationRow.event_id)
    )


_PageRow = Row[
    NotificationRow,
    str,
    str,
    date | None,
    date | None,
    str | None,
    str,
    str,
    UUID | None,
]


def _listed_query() -> Select[
    NotificationRow,
    str,
    str,
    date | None,
    date | None,
    str | None,
    str,
    str,
    UUID | None,
]:
    """Notifications with the current data of their subject (for text and target)."""
    return _with_subjects(
        select(
            NotificationRow,
            # The subject's name: event, invited event or list (only one is joined).
            func.coalesce(EventRow.name, _InvitedEvent.name, SharedListRow.name).label("name"),
            EventRow.city,
            EventRow.start_date,
            EventRow.end_date,
            EventRow.cancel_reason,
            _Actor.first_name.label("actor_first_name"),
            _Actor.last_name.label("actor_last_name"),
            InvitationRow.event_id.label("invited_event_id"),
        )
    )


def _listed(row: _PageRow) -> ListedNotification:
    stored = _stored(row.NotificationRow)
    facts: Facts
    match stored.type.subject:
        case SubjectKind.PERSON:
            facts = PersonFacts(row.actor_first_name or "", row.actor_last_name or "")
        case SubjectKind.LIST:
            facts = ListFacts(row.name or "", row.actor_first_name or "")
        case SubjectKind.INVITATION:
            assert row.invited_event_id is not None  # noqa: S101  # invitation FK cascades
            facts = InvitationFacts(
                row.invited_event_id,
                row.name or "",
                row.actor_first_name or "",
                row.actor_last_name or "",
            )
        case SubjectKind.EVENT:
            facts = EventFacts(row.name, row.city, row.start_date, row.end_date, row.cancel_reason)
    return ListedNotification(stored, facts)


class SqlNotificationStore:
    """Table `notification`; idempotency via `UNIQUE (user_id, dedupe_key)`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the store."""
        self._sessions = sessions

    async def add(
        self,
        user_ids: Sequence[UUID],
        notification_type: NotificationType,
        subject_id: UUID,
        key: str,
        created_at: datetime,
        actor_id: UUID | None = None,
    ) -> list[UUID]:
        """Insert one notification per user, skipping existing `(user, key)` pairs."""
        if not user_ids:
            return []
        subject: dict[str, UUID | None] = {"actor_user_id": actor_id}
        match notification_type.subject:
            case SubjectKind.EVENT:
                subject["event_id"] = subject_id
            case SubjectKind.PERSON:
                subject["actor_user_id"] = subject_id
            case SubjectKind.LIST:
                subject["list_id"] = subject_id
            case SubjectKind.INVITATION:
                subject["invitation_id"] = subject_id
        values = [
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "type": notification_type.value,
                **subject,
                "dedupe_key": key,
                "created_at": created_at,
            }
            for user_id in user_ids
        ]
        async with self._sessions.begin() as session:
            inserted = await session.scalars(
                insert(NotificationRow)
                .values(values)
                .on_conflict_do_nothing(
                    index_elements=[NotificationRow.user_id, NotificationRow.dedupe_key]
                )
                .returning(NotificationRow.id)
            )
            return list(inserted)

    async def page(
        self, user_id: UUID, after: PageCursor | None, limit: int
    ) -> list[ListedNotification]:
        """Newest first, with the current data of the event or person."""
        query = (
            _listed_query()
            .where(NotificationRow.user_id == user_id, _visible())
            .order_by(NotificationRow.created_at.desc(), NotificationRow.id.desc())
            .limit(limit)
        )
        if after is not None:
            query = query.where(
                tuple_(NotificationRow.created_at, NotificationRow.id)
                < tuple_(after.created_at, after.id)
            )
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        return [_listed(row) for row in rows]

    async def unread_count(self, user_id: UUID) -> int:
        """Unread notifications of live events."""
        return (await self.unread_counts([user_id])).get(user_id, 0)

    async def unread_counts(self, user_ids: Sequence[UUID]) -> dict[UUID, int]:
        """Unread notifications per user."""
        if not user_ids:
            return {}
        query = (
            _with_subjects(select(NotificationRow.user_id, func.count()))
            .where(
                NotificationRow.user_id.in_(user_ids),
                NotificationRow.read.is_(False),
                _visible(),
            )
            .group_by(NotificationRow.user_id)
        )
        async with self._sessions() as session:
            counts = {row[0]: row[1] for row in (await session.execute(query)).all()}
        return {user_id: counts.get(user_id, 0) for user_id in user_ids}

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        """Mark one of the user's notifications read."""
        async with self._sessions.begin() as session:
            found = await session.scalar(
                update(NotificationRow)
                .where(NotificationRow.id == notification_id, NotificationRow.user_id == user_id)
                .values(read=True)
                .returning(NotificationRow.id)
            )
        return found is not None

    async def mark_all_read(self, user_id: UUID) -> None:
        """Mark all of the user's notifications read."""
        async with self._sessions.begin() as session:
            await session.execute(
                update(NotificationRow)
                .where(NotificationRow.user_id == user_id, NotificationRow.read.is_(False))
                .values(read=True)
            )

    async def delete(self, user_id: UUID, notification_id: UUID) -> None:
        """Delete the user's notification."""
        async with self._sessions.begin() as session:
            await session.execute(
                delete(NotificationRow).where(
                    NotificationRow.id == notification_id, NotificationRow.user_id == user_id
                )
            )

    async def unpushed(self, ids: Sequence[UUID]) -> list[ListedNotification]:
        """The given notifications not pushed yet (events still live), with their facts."""
        if not ids:
            return []
        query = (
            _listed_query()
            .where(NotificationRow.id.in_(ids), NotificationRow.pushed.is_(False), _visible())
            .order_by(NotificationRow.created_at, NotificationRow.id)
        )
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        return [_listed(row) for row in rows]

    async def mark_pushed(self, ids: Sequence[UUID]) -> None:
        """Set `pushed`."""
        if not ids:
            return
        async with self._sessions.begin() as session:
            await session.execute(
                update(NotificationRow).where(NotificationRow.id.in_(ids)).values(pushed=True)
            )

    async def purge(self, before: datetime) -> int:
        """Delete notifications older than the retention period."""
        async with self._sessions.begin() as session:
            deleted = await session.scalars(
                delete(NotificationRow)
                .where(NotificationRow.created_at < before)
                .returning(NotificationRow.id)
            )
            return len(list(deleted))


def _point(location: GeoPoint) -> ColumnElement[object]:
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(location.lon, location.lat), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )


def _settings(
    row: NotificationSettingsRow, lat: float | None, lon: float | None
) -> NotificationSettings:
    home = None
    if row.home_postal_code and row.home_place_name and lat is not None and lon is not None:
        home = Home(row.home_postal_code, row.home_place_name, GeoPoint(lat, lon))
    return NotificationSettings(
        remind=row.remind,
        remind_days_before=row.remind_days_before,
        near=row.near,
        home=home,
        near_radius_km=row.near_radius_km,
        change=row.change,
        invite=row.invite,
        rsvp=row.rsvp,
    )


class SqlSettingsStore:
    """Table `notification_settings`; no row means the defaults."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the store."""
        self._sessions = sessions

    async def get(self, user_id: UUID) -> NotificationSettings:
        """Settings or defaults."""
        return (await self.for_users([user_id]))[user_id]

    async def for_users(self, user_ids: Sequence[UUID]) -> dict[UUID, NotificationSettings]:
        """Settings of all given users."""
        if not user_ids:
            return {}
        home = cast(NotificationSettingsRow.home_location, Geometry)
        query = select(
            NotificationSettingsRow,
            func.ST_Y(home).label("lat"),
            func.ST_X(home).label("lon"),
        ).where(NotificationSettingsRow.user_id.in_(user_ids))
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        found = {
            row.NotificationSettingsRow.user_id: _settings(
                row.NotificationSettingsRow, row.lat, row.lon
            )
            for row in rows
        }
        return {user_id: found.get(user_id, _DEFAULTS) for user_id in user_ids}

    async def put(self, user_id: UUID, settings: NotificationSettings) -> None:
        """Insert or replace the row."""
        home = settings.home
        values = {
            "remind": settings.remind,
            "remind_days_before": settings.remind_days_before,
            "near": settings.near,
            "home_postal_code": home.postal_code if home else None,
            "home_place_name": home.place_name if home else None,
            "home_location": _point(home.location) if home else None,
            "near_radius_km": settings.near_radius_km,
            "change": settings.change,
            "invite": settings.invite,
            "rsvp": settings.rsvp,
            "updated_at": func.now(),
        }
        statement = insert(NotificationSettingsRow).values(user_id=user_id, **values)
        async with self._sessions.begin() as session:
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[NotificationSettingsRow.user_id], set_=values
                )
            )


class SqlRecipients:
    """Favorites and homes of the users affected by an event."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the query object."""
        self._sessions = sessions

    async def favorite_holders(self, event_id: UUID) -> list[UUID]:
        """Users with the event as favorite."""
        async with self._sessions() as session:
            return list(
                await session.scalars(
                    select(FavoriteRow.user_id)
                    .where(FavoriteRow.event_id == event_id)
                    .order_by(FavoriteRow.user_id)
                )
            )

    async def accepted_invitees(self, event_id: UUID) -> list[UUID]:
        """Users who accepted an invitation to the event."""
        async with self._sessions() as session:
            return list(
                await session.scalars(
                    select(InviteeRow.user_id)
                    .join(InvitationRow, InvitationRow.id == InviteeRow.invitation_id)
                    .where(
                        InvitationRow.event_id == event_id,
                        InviteeRow.status == InviteeStatus.ACCEPTED.value,
                    )
                    .distinct()
                    .order_by(InviteeRow.user_id)
                )
            )

    async def near_home(self, event_id: UUID) -> list[UUID]:
        """Users whose home lies within their radius around the (published) event."""
        query = (
            select(NotificationSettingsRow.user_id)
            .join(
                EventRow,
                and_(
                    EventRow.id == event_id,
                    EventRow.status == EventStatus.PUBLISHED.value,
                    _live_event(),
                    EventRow.location.is_not(None),
                ),
            )
            .where(
                NotificationSettingsRow.home_location.is_not(None),
                func.ST_DWithin(
                    NotificationSettingsRow.home_location,
                    EventRow.location,
                    NotificationSettingsRow.near_radius_km * 1000,
                ),
            )
            .order_by(NotificationSettingsRow.user_id)
        )
        async with self._sessions() as session:
            return list(await session.scalars(query))

    async def reminders(self, today: date) -> dict[UUID, list[UUID]]:
        """Event -> users whose favorite starts `remind_days_before` days from today."""
        days = func.coalesce(
            NotificationSettingsRow.remind_days_before, _DEFAULTS.remind_days_before
        )
        query = (
            select(FavoriteRow.event_id, FavoriteRow.user_id)
            .join(EventRow, EventRow.id == FavoriteRow.event_id)
            .outerjoin(
                NotificationSettingsRow, NotificationSettingsRow.user_id == FavoriteRow.user_id
            )
            .where(
                EventRow.status == EventStatus.PUBLISHED.value,
                _live_event(),
                EventRow.start_date - cast(days, Integer) == today,
            )
            .order_by(FavoriteRow.event_id, FavoriteRow.user_id)
        )
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        result: dict[UUID, list[UUID]] = {}
        for event_id, user_id in rows:
            result.setdefault(event_id, []).append(user_id)
        return result


class SqlDeviceStore:
    """Table `device`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the store."""
        self._sessions = sessions

    async def register(self, user_id: UUID, device: Device, now: datetime) -> None:
        """Upsert by token; the token moves to the user who registered it last."""
        values = {
            "user_id": user_id,
            "platform": device.platform.value,
            "provider": device.provider.value,
            "last_seen_at": now,
        }
        async with self._sessions.begin() as session:
            await session.execute(
                insert(DeviceRow)
                .values(token=device.token, created_at=now, **values)
                .on_conflict_do_update(index_elements=[DeviceRow.token], set_=values)
            )

    async def remove(self, user_id: UUID, token: str) -> None:
        """Delete the user's token."""
        async with self._sessions.begin() as session:
            await session.execute(
                delete(DeviceRow).where(DeviceRow.token == token, DeviceRow.user_id == user_id)
            )

    async def for_users(
        self, user_ids: Sequence[UUID], provider: PushProvider
    ) -> dict[UUID, list[Device]]:
        """Devices per user for the provider."""
        if not user_ids:
            return {}
        query = (
            select(DeviceRow)
            .where(DeviceRow.user_id.in_(user_ids), DeviceRow.provider == provider.value)
            .order_by(DeviceRow.user_id, DeviceRow.token)
        )
        result: dict[UUID, list[Device]] = {}
        async with self._sessions() as session:
            for row in await session.scalars(query):
                result.setdefault(row.user_id, []).append(
                    Device(row.token, DevicePlatform(row.platform), PushProvider(row.provider))
                )
        return result

    async def remove_tokens(self, tokens: Sequence[str]) -> None:
        """Delete invalid tokens."""
        if not tokens:
            return
        async with self._sessions.begin() as session:
            await session.execute(delete(DeviceRow).where(DeviceRow.token.in_(tokens)))

    async def purge_inactive(self, before: datetime) -> int:
        """Delete devices without activity since `before`."""
        async with self._sessions.begin() as session:
            deleted = await session.scalars(
                delete(DeviceRow).where(DeviceRow.last_seen_at < before).returning(DeviceRow.token)
            )
            return len(list(deleted))


class SqlAiSearchOwners:
    """The moderator of an AI search (table `ai_search_job`)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the query object."""
        self._sessions = sessions

    async def moderator_of(self, job_id: UUID) -> UUID | None:
        """Moderator's user ID, None for unknown jobs or deleted accounts."""
        async with self._sessions() as session:
            return await session.scalar(
                select(AiSearchJobRow.moderator_id).where(AiSearchJobRow.id == job_id)
            )
