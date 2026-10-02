"""PostgreSQL implementation of `CategoryRepository` (R09)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Row, case, delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.selectable import ScalarSelect

from stadtfest.adapters.outbound.persistence.models import CategoryRow, EventRow, OutboxRow
from stadtfest.application.moderation.categories import (
    CategoryInUseError,
    DuplicateCategoryNameError,
    ModCategoryView,
)
from stadtfest.domain.events.category import CATEGORY_CHANGED, CategoryDraft

_UNIQUE_NAME = "category_name_key"


def _count_events() -> ScalarSelect[int]:
    """Events per category, all regions and statuses except deleted (R09-US1)."""
    return (
        select(func.count())
        .select_from(EventRow)
        .where(EventRow.category_id == CategoryRow.id, EventRow.deleted_at.is_(None))
        .scalar_subquery()
    )


def _view(row: Row[CategoryRow, int]) -> ModCategoryView:
    category, count = row
    return ModCategoryView(
        id=category.id,
        name=category.name,
        emoji=category.emoji,
        color=category.color,
        active=category.active,
        sort_order=category.sort_order,
        event_count=int(count),
    )


async def _changed(session: AsyncSession, payload: dict[str, object]) -> None:
    await session.execute(
        insert(OutboxRow), [{"id": uuid.uuid4(), "type": CATEGORY_CHANGED, "payload": payload}]
    )


def _duplicate(error: IntegrityError) -> bool:
    return _UNIQUE_NAME in str(error.orig)


class SqlCategoryRepository:
    """Categories in table `category`; changes write `category.changed` to the outbox."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository.

        Args:
            sessions: Session factory of the process.
        """
        self._sessions = sessions

    async def list_all(self) -> list[ModCategoryView]:
        """All categories in chip order, with event counts."""
        query = select(CategoryRow, _count_events()).order_by(
            CategoryRow.sort_order, CategoryRow.name
        )
        async with self._sessions() as session:
            return [_view(row) for row in (await session.execute(query)).all()]

    async def get(self, category_id: UUID) -> ModCategoryView | None:
        """One category, or None."""
        query = select(CategoryRow, _count_events()).where(CategoryRow.id == category_id)
        async with self._sessions() as session:
            row = (await session.execute(query)).one_or_none()
        return _view(row) if row else None

    async def add(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView:
        """Insert at the end of the order."""
        try:
            async with self._sessions.begin() as session:
                last = await session.scalar(select(func.max(CategoryRow.sort_order)))
                session.add(
                    CategoryRow(
                        id=category_id,
                        name=draft.name,
                        emoji=draft.emoji,
                        color=draft.color,
                        active=draft.active,
                        sort_order=(last if last is not None else -1) + 1,
                    )
                )
                await session.flush()
                await _changed(session, {"categoryId": str(category_id)})
        except IntegrityError as error:
            if _duplicate(error):
                raise DuplicateCategoryNameError from None
            raise
        created = await self.get(category_id)
        if created is None:  # unreachable: inserted above
            raise RuntimeError("category vanished")
        return created

    async def update(self, category_id: UUID, draft: CategoryDraft) -> ModCategoryView | None:
        """Store all fields."""
        try:
            async with self._sessions.begin() as session:
                found = await session.scalar(
                    update(CategoryRow)
                    .where(CategoryRow.id == category_id)
                    .values(
                        name=draft.name,
                        emoji=draft.emoji,
                        color=draft.color,
                        active=draft.active,
                        updated_at=datetime.now(UTC),
                    )
                    .returning(CategoryRow.id)
                )
                if found is None:
                    return None
                await _changed(session, {"categoryId": str(category_id)})
        except IntegrityError as error:
            if _duplicate(error):
                raise DuplicateCategoryNameError from None
            raise
        return await self.get(category_id)

    async def reorder(self, category_ids: Sequence[UUID]) -> None:
        """Set `sort_order` 0..n-1 in the given order."""
        positions = {category_id: index for index, category_id in enumerate(category_ids)}
        async with self._sessions.begin() as session:
            await session.execute(
                update(CategoryRow)
                .where(CategoryRow.id.in_(category_ids))
                .values(sort_order=case(positions, value=CategoryRow.id))
            )
            await _changed(session, {"order": True})

    async def delete(self, category_id: UUID, replacement_id: UUID | None) -> int | None:
        """Move all events (also deleted ones) and delete, in one transaction.

        Returns the number of moved, not deleted events (shown to the moderator).
        """
        async with self._sessions.begin() as session:
            exists = await session.scalar(
                select(CategoryRow.id).where(CategoryRow.id == category_id).with_for_update()
            )
            if exists is None:
                return None
            using = (
                await session.execute(
                    select(
                        func.count(),
                        func.count().filter(EventRow.deleted_at.is_(None)),
                    ).where(EventRow.category_id == category_id)
                )
            ).one()
            total, visible = int(using[0]), int(using[1])
            if total and replacement_id is None:
                raise CategoryInUseError
            if total:
                await session.execute(
                    update(EventRow)
                    .where(EventRow.category_id == category_id)
                    .values(category_id=replacement_id)
                )
            await session.execute(delete(CategoryRow).where(CategoryRow.id == category_id))
            await _changed(
                session,
                {
                    "categoryId": str(category_id),
                    "replacementId": str(replacement_id) if replacement_id else None,
                },
            )
        return visible
