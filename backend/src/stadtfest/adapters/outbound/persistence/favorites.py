"""PostgreSQL implementation of the favorites port (R06)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import ColumnElement, cast, delete, func, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.covers import cover_lateral, cover_view
from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    CategoryRow,
    EventRow,
    FavoriteRow,
)
from stadtfest.adapters.outbound.storage.urls import ImageUrls
from stadtfest.application.collections.ports import FavoriteView
from stadtfest.application.events.views import EventSummaryView
from stadtfest.domain.events.event import PUBLIC_STATUSES, EventStatus
from stadtfest.domain.events.geo import GeoPoint

_PUBLIC_STATUS_VALUES = sorted(status.value for status in PUBLIC_STATUSES)


def _publicly_visible() -> list[ColumnElement[bool]]:
    return [EventRow.status.in_(_PUBLIC_STATUS_VALUES), EventRow.deleted_at.is_(None)]


def _user_id(subject: str) -> ColumnElement[UUID]:
    return select(AppUserRow.id).where(AppUserRow.idp_subject == subject).scalar_subquery()


class SqlFavoriteRepository:
    """Favorites in table `favorite`; `event.favorite_count` is kept in the same transaction."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], image_urls: ImageUrls) -> None:
        """Create the repository.

        Args:
            sessions: Session factory.
            image_urls: Builds the public URLs of cover images.
        """
        self._sessions = sessions
        self._urls = image_urls

    async def add(self, subject: str, event_id: UUID) -> bool:
        """Insert the favorite once; count it only if it was new."""
        async with self._sessions.begin() as session:
            visible = await session.scalar(
                select(EventRow.id).where(EventRow.id == event_id, *_publicly_visible())
            )
            if visible is None:
                return False
            inserted = await session.scalar(
                insert(FavoriteRow)
                .values(user_id=_user_id(subject), event_id=event_id)
                .on_conflict_do_nothing()
                .returning(FavoriteRow.event_id)
            )
            if inserted is not None:
                await session.execute(
                    update(EventRow)
                    .where(EventRow.id == event_id)
                    .values(favorite_count=EventRow.favorite_count + 1)
                )
            return True

    async def remove(self, subject: str, event_id: UUID) -> None:
        """Delete the favorite; decrement the counter only if one was deleted."""
        async with self._sessions.begin() as session:
            removed = await session.scalar(
                delete(FavoriteRow)
                .where(FavoriteRow.user_id == _user_id(subject), FavoriteRow.event_id == event_id)
                .returning(FavoriteRow.event_id)
            )
            if removed is not None:
                await session.execute(
                    update(EventRow)
                    .where(EventRow.id == event_id)
                    .values(favorite_count=func.greatest(EventRow.favorite_count - 1, 0))
                )

    async def list_for(self, subject: str, *, from_day: date | None) -> list[FavoriteView]:
        """Favorites of publicly visible events, ordered by start date and name."""
        cover = cover_lateral()
        query = (
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
                CategoryRow.name.label("category_name"),
                CategoryRow.emoji,
                FavoriteRow.created_at.label("favorited_at"),
                cover.c.id.label("cover_id"),
                cover.c.width.label("cover_width"),
                cover.c.height.label("cover_height"),
            )
            .join(EventRow, EventRow.id == FavoriteRow.event_id)
            .join(CategoryRow, CategoryRow.id == EventRow.category_id)
            .outerjoin(cover, true())
            .where(FavoriteRow.user_id == _user_id(subject), *_publicly_visible())
            .order_by(EventRow.start_date, EventRow.name, EventRow.id)
        )
        if from_day is not None:
            query = query.where(EventRow.end_date >= from_day)
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        return [
            FavoriteView(
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
                favorited_at=row.favorited_at,
            )
            for row in rows
        ]

    async def is_favorite(self, subject: str, event_id: UUID) -> bool:
        """Return True if the favorite exists."""
        async with self._sessions() as session:
            found = await session.scalar(
                select(FavoriteRow.event_id).where(
                    FavoriteRow.user_id == _user_id(subject), FavoriteRow.event_id == event_id
                )
            )
        return found is not None
