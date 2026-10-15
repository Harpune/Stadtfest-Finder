"""PostgreSQL implementation of the shared list repository (R13)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import cast, delete, exists, func, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.covers import cover_lateral, cover_view
from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    CategoryRow,
    EventRow,
    ListEventRow,
    ListMemberRow,
    OutboxRow,
    SharedListRow,
)
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.collections.lists import (
    ListEventView,
    ListMemberView,
    SharedListView,
)
from stadtfest.application.events.views import EventSummaryView
from stadtfest.domain.collections.lists import ListEventType
from stadtfest.domain.events.event import PUBLIC_STATUSES, EventStatus
from stadtfest.domain.events.geo import GeoPoint

_PUBLIC = sorted(status.value for status in PUBLIC_STATUSES)


def _members_added(list_id: UUID, user_ids: Sequence[UUID], actor: UUID) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "type": ListEventType.MEMBERS_ADDED.value,
        "payload": {
            "listId": str(list_id),
            "userIds": [str(user_id) for user_id in user_ids],
            "actorId": str(actor),
        },
    }


class SqlSharedListRepository:
    """Tables `shared_list`, `list_member` and `list_event`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], image_urls: ImageUrls) -> None:
        """Create the repository."""
        self._sessions = sessions
        self._urls = image_urls

    async def lists_of(self, user_id: UUID) -> list[SharedListView]:
        """All lists of the user."""
        async with self._sessions() as session:
            ids = list(
                await session.scalars(
                    select(ListMemberRow.list_id).where(ListMemberRow.user_id == user_id)
                )
            )
            return await self._views(session, ids)

    async def get(self, list_id: UUID) -> SharedListView | None:
        """One list."""
        async with self._sessions() as session:
            views = await self._views(session, [list_id])
        return views[0] if views else None

    async def is_member(self, list_id: UUID, user_id: UUID) -> bool:
        """Whether the user is a member."""
        async with self._sessions() as session:
            found = await session.scalar(
                select(ListMemberRow.user_id).where(
                    ListMemberRow.list_id == list_id, ListMemberRow.user_id == user_id
                )
            )
        return found is not None

    async def create(
        self, list_id: UUID, name: str, creator: UUID, members: Sequence[UUID], now: datetime
    ) -> None:
        """List, memberships and `list.members_added` in one transaction."""
        rows = [
            {"list_id": list_id, "user_id": user_id, "added_by": creator, "added_at": now}
            for user_id in [creator, *members]
        ]
        async with self._sessions.begin() as session:
            await session.execute(
                insert(SharedListRow).values(
                    id=list_id, name=name, created_by=creator, created_at=now
                )
            )
            await session.execute(insert(ListMemberRow), rows)
            if members:
                await session.execute(
                    insert(OutboxRow).values(**_members_added(list_id, members, creator))
                )

    async def rename(self, list_id: UUID, name: str) -> None:
        """Set the name."""
        async with self._sessions.begin() as session:
            await session.execute(
                update(SharedListRow).where(SharedListRow.id == list_id).values(name=name)
            )

    async def delete(self, list_id: UUID) -> None:
        """Delete the list (members and events cascade)."""
        async with self._sessions.begin() as session:
            await session.execute(delete(SharedListRow).where(SharedListRow.id == list_id))

    async def add_member(self, list_id: UUID, user_id: UUID, by: UUID, now: datetime) -> None:
        """Insert the membership once; only a new one writes the outbox event."""
        async with self._sessions.begin() as session:
            added = await session.scalar(
                insert(ListMemberRow)
                .values(list_id=list_id, user_id=user_id, added_by=by, added_at=now)
                .on_conflict_do_nothing()
                .returning(ListMemberRow.user_id)
            )
            if added is not None:
                await session.execute(
                    insert(OutboxRow).values(**_members_added(list_id, [user_id], by))
                )

    async def remove_member(self, list_id: UUID, user_id: UUID) -> None:
        """Delete the membership; delete the list if nobody is left."""
        async with self._sessions.begin() as session:
            # Lock the list so two members leaving at once cannot both see "one left".
            await session.execute(
                select(SharedListRow.id).where(SharedListRow.id == list_id).with_for_update()
            )
            await session.execute(
                delete(ListMemberRow).where(
                    ListMemberRow.list_id == list_id, ListMemberRow.user_id == user_id
                )
            )
            await session.execute(
                delete(SharedListRow).where(
                    SharedListRow.id == list_id,
                    ~exists().where(ListMemberRow.list_id == SharedListRow.id),
                )
            )

    async def add_event(self, list_id: UUID, event_id: UUID, by: UUID, now: datetime) -> bool:
        """Insert the event once if it is publicly visible."""
        async with self._sessions.begin() as session:
            visible = await session.scalar(
                select(EventRow.id).where(
                    EventRow.id == event_id,
                    EventRow.status.in_(_PUBLIC),
                    EventRow.deleted_at.is_(None),
                )
            )
            if visible is None:
                return False
            await session.execute(
                insert(ListEventRow)
                .values(list_id=list_id, event_id=event_id, added_by=by, added_at=now)
                .on_conflict_do_nothing()
            )
            return True

    async def remove_event(self, list_id: UUID, event_id: UUID) -> None:
        """Delete the event from the list."""
        async with self._sessions.begin() as session:
            await session.execute(
                delete(ListEventRow).where(
                    ListEventRow.list_id == list_id, ListEventRow.event_id == event_id
                )
            )

    async def _views(self, session: AsyncSession, ids: Sequence[UUID]) -> list[SharedListView]:
        if not ids:
            return []
        lists = (
            await session.execute(
                select(SharedListRow.id, SharedListRow.name).where(SharedListRow.id.in_(ids))
            )
        ).all()
        members = (
            await session.execute(
                select(
                    ListMemberRow.list_id,
                    AppUserRow.id,
                    AppUserRow.first_name,
                    AppUserRow.last_name,
                )
                .join(AppUserRow, AppUserRow.id == ListMemberRow.user_id)
                .where(ListMemberRow.list_id.in_(ids))
                .order_by(ListMemberRow.added_at, AppUserRow.first_name, AppUserRow.id)
            )
        ).all()
        cover = cover_lateral()
        events = (
            await session.execute(
                select(
                    ListEventRow.list_id,
                    ListEventRow.added_at,
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
                    CategoryRow.name.label("category_name"),
                    CategoryRow.emoji,
                    cover.c.id.label("cover_id"),
                    cover.c.width.label("cover_width"),
                    cover.c.height.label("cover_height"),
                )
                .join(EventRow, EventRow.id == ListEventRow.event_id)
                .join(CategoryRow, CategoryRow.id == EventRow.category_id)
                .outerjoin(cover, true())
                .where(
                    ListEventRow.list_id.in_(ids),
                    # Deleted and unpublished events disappear from lists (R13-US3).
                    EventRow.status.in_(_PUBLIC),
                    EventRow.deleted_at.is_(None),
                )
                .order_by(EventRow.start_date, EventRow.name, EventRow.id)
            )
        ).all()
        by_list_members: dict[UUID, list[ListMemberView]] = {}
        for member in members:
            by_list_members.setdefault(member.list_id, []).append(
                ListMemberView(member.id, member.first_name, member.last_name)
            )
        by_list_events: dict[UUID, list[ListEventView]] = {}
        for row in events:
            by_list_events.setdefault(row.list_id, []).append(
                ListEventView(
                    event=EventSummaryView(
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
                        cover_image=cover_view(row, self._urls),
                    ),
                    category_name=row.category_name,
                    emoji=row.emoji,
                    added_at=row.added_at,
                )
            )
        return [
            SharedListView(
                id=entry.id,
                name=entry.name,
                members=by_list_members.get(entry.id, []),
                events=by_list_events.get(entry.id, []),
            )
            for entry in lists
        ]
