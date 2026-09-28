"""PostgreSQL/PostGIS implementation of the public catalog ports."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    ColumnElement,
    Numeric,
    and_,
    case,
    cast,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import CategoryRow, EventRow, ProgramItemRow
from stadtfest.application.events.criteria import PageCursor, SearchCriteria, SearchFilter
from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventDetailView,
    EventSummaryView,
    ProgramItemView,
)
from stadtfest.domain.events.event import PUBLIC_STATUSES, EventStatus
from stadtfest.domain.events.geo import GeoPoint

# Minimum pg_trgm word similarity for typo-tolerant text search.
WORD_SIMILARITY_THRESHOLD = 0.4

_PUBLIC_STATUS_VALUES = sorted(status.value for status in PUBLIC_STATUSES)


def _point(location: GeoPoint) -> ColumnElement[object]:
    return cast(
        func.ST_SetSRID(func.ST_MakePoint(location.lon, location.lat), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )


def _lat() -> ColumnElement[float]:
    return func.ST_Y(cast(EventRow.location, Geometry))


def _lon() -> ColumnElement[float]:
    return func.ST_X(cast(EventRow.location, Geometry))


def _distance_km(reference: GeoPoint | None) -> ColumnElement[float | None]:
    if reference is None:
        return literal(None)
    meters = func.ST_Distance(EventRow.location, _point(reference))
    return func.round(cast(meters / 1000, Numeric), 1)


class SqlCatalog:
    """Implements `EventCatalog` and `CategoryCatalog` with PostGIS queries."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the adapter.

        Args:
            sessions: Session factory of the process.
        """
        self._sessions = sessions

    # ---- CategoryCatalog -------------------------------------------------------------

    async def list_active(self) -> list[CategoryView]:
        """Return active categories in moderation order."""
        query = (
            select(CategoryRow)
            .where(CategoryRow.active.is_(True))
            .order_by(CategoryRow.sort_order, CategoryRow.name)
        )
        async with self._sessions() as session:
            rows = (await session.scalars(query)).all()
        return [_category_view(row) for row in rows]

    # ---- EventCatalog ----------------------------------------------------------------

    async def search(
        self, criteria: SearchCriteria, after: PageCursor | None, limit: int
    ) -> list[EventSummaryView]:
        """Return listed events in public order (running first, start date, name, id)."""
        upcoming = case((EventRow.start_date > criteria.today, 1), else_=0)
        reference = criteria.filter.distance_reference
        query = select(
            EventRow.id,
            EventRow.name,
            EventRow.short_name,
            EventRow.status,
            EventRow.start_date,
            EventRow.end_date,
            EventRow.place,
            EventRow.city,
            EventRow.category_id,
            _lat().label("lat"),
            _lon().label("lon"),
            _distance_km(reference).label("distance_km"),
        )
        async with self._sessions() as session:
            query = query.where(*await self._conditions(session, criteria, criteria.filter))
            if after is not None:
                query = query.where(
                    tuple_(upcoming, EventRow.start_date, EventRow.name, EventRow.id)
                    > tuple_(int(after.upcoming), after.start_date, after.name, after.id)
                )
            query = query.order_by(upcoming, EventRow.start_date, EventRow.name, EventRow.id)
            rows = (await session.execute(query.limit(limit))).all()
        return [
            EventSummaryView(
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
                distance_km=float(row.distance_km) if row.distance_km is not None else None,
            )
            for row in rows
        ]

    async def count(self, criteria: SearchCriteria) -> EventCountView:
        """Count with all filters, and per category without the category filter."""
        async with self._sessions() as session:
            total_query = select(func.count()).select_from(EventRow)
            total_query = total_query.where(
                *await self._conditions(session, criteria, criteria.filter)
            )
            total = (await session.execute(total_query)).scalar_one()

            per_category = (
                select(EventRow.category_id, func.count())
                .where(
                    *await self._conditions(session, criteria, criteria.filter.without_categories())
                )
                .group_by(EventRow.category_id)
            )
            rows = (await session.execute(per_category)).all()
        return EventCountView(
            total=int(total),
            by_category={
                category_id: int(amount) for category_id, amount in rows if category_id is not None
            },
        )

    async def get_public(
        self, event_id: UUID, reference: GeoPoint | None
    ) -> EventDetailView | None:
        """Return a published or cancelled, non-deleted event (also after it ended)."""
        query = (
            select(
                EventRow,
                CategoryRow,
                _lat().label("lat"),
                _lon().label("lon"),
                _distance_km(reference).label("distance_km"),
            )
            .join(CategoryRow, CategoryRow.id == EventRow.category_id)
            .where(
                EventRow.id == event_id,
                EventRow.status.in_(_PUBLIC_STATUS_VALUES),
                EventRow.deleted_at.is_(None),
            )
        )
        program_query = (
            select(ProgramItemRow)
            .where(ProgramItemRow.event_id == event_id)
            .order_by(ProgramItemRow.date, ProgramItemRow.position)
        )
        async with self._sessions() as session:
            row = (await session.execute(query)).one_or_none()
            if row is None:
                return None
            program = (await session.scalars(program_query)).all()
        event: EventRow = row[0]
        if event.start_date is None or event.end_date is None:
            return None  # unreachable: the DB check requires dates for public events
        return EventDetailView(
            id=event.id,
            name=event.name,
            short_name=event.short_name,
            status=EventStatus(event.status),
            cancel_reason=event.cancel_reason,
            category=_category_view(row[1]),
            start_date=event.start_date,
            end_date=event.end_date,
            opening_hours=tuple(event.opening_hours),
            price=event.price,
            place=event.place,
            address=event.address,
            city=event.city,
            postal_code=event.postal_code or "",
            location=GeoPoint(row.lat, row.lon),
            description=event.description,
            program=tuple(
                ProgramItemView(item.date, item.time_label, item.title, item.subtitle)
                for item in program
            ),
            transit=event.transit,
            parking=event.parking,
            website_url=event.website_url,
            distance_km=float(row.distance_km) if row.distance_km is not None else None,
        )

    # ---- query building ----------------------------------------------------------------

    async def _conditions(
        self, session: AsyncSession, criteria: SearchCriteria, search_filter: SearchFilter
    ) -> Sequence[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [
            EventRow.status.in_(_PUBLIC_STATUS_VALUES),
            EventRow.deleted_at.is_(None),
            EventRow.end_date >= criteria.today,
        ]
        if search_filter.bbox is not None:
            box = search_filter.bbox
            envelope = cast(
                func.ST_MakeEnvelope(box.min_lon, box.min_lat, box.max_lon, box.max_lat, 4326),
                Geography(srid=4326),
            )
            conditions.append(func.ST_Intersects(EventRow.location, envelope))
        if search_filter.reference is not None:
            conditions.append(
                func.ST_DWithin(
                    EventRow.location,
                    _point(search_filter.reference),
                    search_filter.radius_km * 1000,
                )
            )
        if criteria.windows is not None:
            conditions.append(
                or_(
                    *(
                        and_(EventRow.start_date <= window.end, EventRow.end_date >= window.start)
                        for window in criteria.windows
                    )
                )
            )
        if search_filter.category_ids:
            active = await self._active_category_ids(session, search_filter.category_ids)
            # Unknown or inactive IDs are ignored silently (workflow 10, rules).
            if active:
                conditions.append(EventRow.category_id.in_(active))
        if search_filter.text:
            normalized = func.immutable_unaccent(func.lower(search_filter.text.strip()))
            conditions.append(
                or_(
                    func.strpos(EventRow.search_text, normalized) > 0,
                    func.word_similarity(normalized, EventRow.search_text)
                    >= WORD_SIMILARITY_THRESHOLD,
                )
            )
        return conditions or [true()]

    @staticmethod
    async def _active_category_ids(session: AsyncSession, requested: frozenset[UUID]) -> list[UUID]:
        query = select(CategoryRow.id).where(
            CategoryRow.id.in_(requested), CategoryRow.active.is_(True)
        )
        return list((await session.scalars(query)).all())


def _category_view(row: CategoryRow) -> CategoryView:
    return CategoryView(
        id=row.id, name=row.name, emoji=row.emoji, color=row.color, sort_order=row.sort_order
    )
