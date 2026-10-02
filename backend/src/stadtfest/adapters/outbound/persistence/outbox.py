"""PostgreSQL outbox (ADR 0005): pending messages are locked with `SKIP LOCKED` while sent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import FavoriteRow, OutboxRow
from stadtfest.application.outbox.ports import OutboxMessage


class SqlOutboxStore:
    """Reads and marks messages in table `outbox`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the store.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def dispatch_pending(
        self, limit: int, send: Callable[[OutboxMessage], Awaitable[None]]
    ) -> int:
        """Send pending messages in order and mark them dispatched in one transaction."""
        async with self._sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(OutboxRow)
                    .where(OutboxRow.dispatched_at.is_(None))
                    .order_by(OutboxRow.occurred_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                await send(OutboxMessage(row.id, row.type, dict(row.payload)))
            if rows:
                await session.execute(
                    update(OutboxRow)
                    .where(OutboxRow.id.in_([row.id for row in rows]))
                    .values(dispatched_at=func.now())
                )
            return len(rows)

    async def purge_dispatched(self, before: datetime) -> int:
        """Delete messages dispatched before `before`."""
        async with self._sessions.begin() as session:
            result = await session.execute(
                delete(OutboxRow)
                .where(OutboxRow.dispatched_at.is_not(None), OutboxRow.dispatched_at < before)
                .returning(OutboxRow.id)
            )
            return len(result.all())


class SqlEventFavorites:
    """Favorites of an event in table `favorite`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the adapter.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def remove_for_event(self, event_id: UUID) -> int:
        """Delete all favorites of the event."""
        async with self._sessions.begin() as session:
            result = await session.execute(
                delete(FavoriteRow)
                .where(FavoriteRow.event_id == event_id)
                .returning(FavoriteRow.user_id)
            )
            return len(result.all())
