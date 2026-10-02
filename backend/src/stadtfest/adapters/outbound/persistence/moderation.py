"""PostgreSQL implementation of the moderation ports (R07).

Every change writes its domain events into `outbox` in the same transaction (ADR 0005).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import ColumnElement, cast, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.images import image_from_row
from stadtfest.adapters.outbound.persistence.models import (
    CategoryRow,
    EventImageRow,
    EventRow,
    OutboxRow,
    ProgramItemRow,
    RegionRow,
    RejectedSourceRow,
)
from stadtfest.application.moderation.ports import (
    ModEventSummary,
    ModRegion,
    VersionConflictError,
)
from stadtfest.domain.ai_ingestion.finds import normalize_url
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.images import EventImage
from stadtfest.domain.events.maintenance import (
    DomainEvent,
    EventContent,
    ManagedEvent,
    ProgramEntry,
)
from stadtfest.domain.events.region import Region


def _location(content: EventContent) -> ColumnElement[object] | None:
    if content.lat is None or content.lon is None:
        return None
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(content.lon, content.lat), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )


def event_columns(event: ManagedEvent) -> dict[str, object]:
    """Column values of the event row (without id, version and audit fields)."""
    c = event.content
    return {
        "region_id": event.region_id,
        "name": c.name,
        "short_name": c.short_name,
        "category_id": c.category_id,
        "status": event.status.value,
        "start_date": c.start_date,
        "end_date": c.end_date,
        "opening_hours": list(c.opening_hours),
        "price": c.price,
        "place": c.place,
        "address": c.address,
        "city": c.city,
        "postal_code": c.postal_code,
        "location": _location(c),
        "description": c.description,
        "transit": c.transit,
        "parking": c.parking,
        "website_url": c.website_url,
        "cancel_reason": c.cancel_reason,
        "published_at": event.published_at,
    }


def outbox_values(events: Sequence[DomainEvent]) -> list[dict[str, object]]:
    """Outbox rows for domain events; payloads carry IDs and field names only."""
    return [
        {
            "id": uuid.uuid4(),
            "type": event.type.value,
            "payload": {
                "eventId": str(event.event_id),
                "changedFields": list(event.changed_fields),
            },
        }
        for event in events
    ]


async def _write_program(session: AsyncSession, event: ManagedEvent) -> None:
    await session.execute(delete(ProgramItemRow).where(ProgramItemRow.event_id == event.id))
    if event.content.program:
        await session.execute(
            insert(ProgramItemRow),
            [
                {
                    "id": uuid.uuid4(),
                    "event_id": event.id,
                    "date": entry.date,
                    "time_label": entry.time_label,
                    "title": entry.title,
                    "subtitle": entry.subtitle,
                    "position": position,
                }
                for position, entry in enumerate(event.content.program)
            ],
        )


async def _write_outbox(session: AsyncSession, event: ManagedEvent) -> None:
    if event.pending_events:
        await session.execute(insert(OutboxRow), outbox_values(event.pending_events))
        event.pending_events.clear()


class SqlManagedEventRepository:
    """Events of the moderation view in tables `event` and `program_item`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def list_for_region(
        self, region_id: UUID, ids: frozenset[UUID] | None
    ) -> list[ModEventSummary]:
        """All non-deleted events of the region, optionally restricted to `ids`."""
        query = select(
            EventRow.id,
            EventRow.name,
            EventRow.status,
            EventRow.start_date,
            EventRow.end_date,
            EventRow.place,
            EventRow.city,
            EventRow.category_id,
            EventRow.favorite_count,
            EventRow.source,
            EventRow.version,
        ).where(EventRow.region_id == region_id, EventRow.deleted_at.is_(None))
        if ids is not None:
            query = query.where(EventRow.id.in_(ids))
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        return [
            ModEventSummary(
                id=row.id,
                name=row.name,
                status=EventStatus(row.status),
                start_date=row.start_date,
                end_date=row.end_date,
                place=row.place,
                city=row.city,
                category_id=row.category_id,
                favorite_count=row.favorite_count,
                source=row.source,
                version=row.version,
            )
            for row in rows
        ]

    async def list_images(self, event_id: UUID) -> list[EventImage]:
        """The event's images ordered by position (R08)."""
        async with self._sessions() as session:
            rows = await session.scalars(
                select(EventImageRow)
                .where(EventImageRow.event_id == event_id)
                .order_by(EventImageRow.position)
            )
            return [image_from_row(row) for row in rows]

    async def get(self, event_id: UUID) -> ManagedEvent | None:
        """The non-deleted event with its program."""
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(
                        EventRow,
                        func.ST_Y(cast(EventRow.location, Geometry)).label("lat"),
                        func.ST_X(cast(EventRow.location, Geometry)).label("lon"),
                    ).where(EventRow.id == event_id, EventRow.deleted_at.is_(None))
                )
            ).one_or_none()
            if row is None:
                return None
            program = (
                await session.scalars(
                    select(ProgramItemRow)
                    .where(ProgramItemRow.event_id == event_id)
                    .order_by(ProgramItemRow.position, ProgramItemRow.date)
                )
            ).all()
        event: EventRow = row.EventRow
        content = EventContent(
            name=event.name,
            short_name=event.short_name,
            category_id=event.category_id,
            start_date=event.start_date,
            end_date=event.end_date,
            opening_hours=tuple(event.opening_hours or ()),
            price=event.price,
            place=event.place,
            address=event.address,
            city=event.city,
            postal_code=event.postal_code,
            lat=row.lat,
            lon=row.lon,
            description=event.description,
            program=tuple(
                ProgramEntry(item.date, item.time_label, item.title, item.subtitle)
                for item in program
            ),
            transit=event.transit,
            parking=event.parking,
            website_url=event.website_url,
            cancel_reason=event.cancel_reason,
        )
        return ManagedEvent(
            id=event.id,
            region_id=event.region_id,
            status=EventStatus(event.status),
            content=content,
            version=event.version,
            favorite_count=event.favorite_count,
            source=event.source,
            source_url=event.source_url,
            ai_job_id=event.ai_job_id,
            found_at=event.found_at,
            published_at=event.published_at,
        )

    async def add(self, event: ManagedEvent, user_id: UUID) -> None:
        """Insert the event, its program and pending domain events."""
        async with self._sessions.begin() as session:
            await session.execute(
                insert(EventRow).values(
                    id=event.id,
                    version=1,
                    source=event.source,
                    source_url=event.source_url,
                    ai_job_id=event.ai_job_id,
                    found_at=event.found_at,
                    created_by=user_id,
                    updated_by=user_id,
                    **event_columns(event),
                )
            )
            await _write_program(session, event)
            await _write_outbox(session, event)
        event.version = 1

    async def save(self, event: ManagedEvent, expected_version: int, user_id: UUID) -> int:
        """Update the row if the version matches; program and outbox in the same transaction."""
        values = event_columns(event) | {
            "version": EventRow.version + 1,
            "updated_by": user_id,
            "updated_at": func.now(),
        }
        if event.deleted:
            values["deleted_at"] = func.now()
        async with self._sessions.begin() as session:
            version = await session.scalar(
                update(EventRow)
                .where(
                    EventRow.id == event.id,
                    EventRow.version == expected_version,
                    EventRow.deleted_at.is_(None),
                )
                .values(**values)
                .returning(EventRow.version)
            )
            if version is None:
                raise VersionConflictError
            await _write_program(session, event)
            await _write_outbox(session, event)
            if event.deleted and event.source == "ai" and event.source_url:
                # A discarded AI find is never suggested again in this region (R10-US4).
                await session.execute(
                    pg_insert(RejectedSourceRow)
                    .values(
                        region_id=event.region_id, url_normalized=normalize_url(event.source_url)
                    )
                    .on_conflict_do_nothing()
                )
        return int(version)


class SqlModRegionDirectory:
    """Regions with their postal codes."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the directory.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def by_key(self, key: str) -> ModRegion | None:
        """The region with this key, or None."""
        async with self._sessions() as session:
            row = await session.scalar(select(RegionRow).where(RegionRow.key == key))
        if row is None:
            return None
        return ModRegion(row.id, Region(row.key, row.name, frozenset(row.postal_codes or ())))

    async def by_id(self, region_id: UUID) -> ModRegion | None:
        """The region with this ID, or None."""
        async with self._sessions() as session:
            row = await session.get(RegionRow, region_id)
        if row is None:
            return None
        return ModRegion(row.id, Region(row.key, row.name, frozenset(row.postal_codes or ())))


class SqlActiveCategories:
    """Active categories from table `category`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the adapter.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def active_ids(self) -> frozenset[UUID]:
        """IDs of the active categories."""
        async with self._sessions() as session:
            ids = await session.scalars(select(CategoryRow.id).where(CategoryRow.active))
            return frozenset(ids)
