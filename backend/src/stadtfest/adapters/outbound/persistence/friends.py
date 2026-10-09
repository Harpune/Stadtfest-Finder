"""PostgreSQL implementation of the friend repository (R12)."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    FriendLinkRow,
    FriendshipRow,
    OutboxRow,
)
from stadtfest.application.collections.friends import FriendLinkView, FriendView, LinkTarget
from stadtfest.domain.collections.friends import FriendEventType


class SqlFriendRepository:
    """Tables `friend_link` and `friendship` (symmetric, two rows per friendship)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository."""
        self._sessions = sessions

    async def link_of(self, user_id: UUID) -> FriendLinkView | None:
        """The user's current link."""
        async with self._sessions() as session:
            row = await session.get(FriendLinkRow, user_id)
        return FriendLinkView(row.token, row.created_at) if row else None

    async def set_link(self, user_id: UUID, token: str, now: datetime) -> FriendLinkView:
        """Insert or replace the user's token."""
        values = {"token": token, "created_at": now}
        async with self._sessions.begin() as session:
            await session.execute(
                insert(FriendLinkRow)
                .values(user_id=user_id, **values)
                .on_conflict_do_update(index_elements=[FriendLinkRow.user_id], set_=values)
            )
        return FriendLinkView(token, now)

    async def owner_of(self, token: str) -> LinkTarget | None:
        """The owner of a current token."""
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(AppUserRow.id, AppUserRow.first_name, AppUserRow.last_name)
                    .join(FriendLinkRow, FriendLinkRow.user_id == AppUserRow.id)
                    .where(FriendLinkRow.token == token)
                )
            ).one_or_none()
        return LinkTarget(row.id, row.first_name, row.last_name) if row else None

    async def befriend(self, owner_id: UUID, friend_id: UUID, now: datetime) -> FriendView:
        """Both directions plus `friendship.created` in one transaction, unless it exists."""
        async with self._sessions.begin() as session:
            created = await session.scalars(
                insert(FriendshipRow)
                .values(
                    [
                        {"user_id": owner_id, "friend_id": friend_id, "created_at": now},
                        {"user_id": friend_id, "friend_id": owner_id, "created_at": now},
                    ]
                )
                .on_conflict_do_nothing()
                .returning(FriendshipRow.user_id)
            )
            if list(created):
                await session.execute(
                    insert(OutboxRow).values(
                        id=uuid.uuid4(),
                        type=FriendEventType.CREATED.value,
                        payload={"userId": str(owner_id), "friendId": str(friend_id)},
                    )
                )
            row = (
                await session.execute(
                    select(AppUserRow.first_name, AppUserRow.last_name, FriendshipRow.created_at)
                    .join(FriendshipRow, FriendshipRow.friend_id == AppUserRow.id)
                    .where(FriendshipRow.user_id == friend_id, FriendshipRow.friend_id == owner_id)
                )
            ).one()
        return FriendView(owner_id, row.first_name, row.last_name, row.created_at)

    async def friends_of(self, user_id: UUID) -> list[FriendView]:
        """Friends ordered by first and last name."""
        query = (
            select(
                AppUserRow.id, AppUserRow.first_name, AppUserRow.last_name, FriendshipRow.created_at
            )
            .join(FriendshipRow, FriendshipRow.friend_id == AppUserRow.id)
            .where(FriendshipRow.user_id == user_id)
            .order_by(AppUserRow.first_name, AppUserRow.last_name, AppUserRow.id)
        )
        async with self._sessions() as session:
            rows = (await session.execute(query)).all()
        return [FriendView(r.id, r.first_name, r.last_name, r.created_at) for r in rows]

    async def remove(self, user_id: UUID, friend_id: UUID) -> None:
        """Delete both directions."""
        async with self._sessions.begin() as session:
            await session.execute(
                delete(FriendshipRow).where(
                    or_(
                        (FriendshipRow.user_id == user_id) & (FriendshipRow.friend_id == friend_id),
                        (FriendshipRow.user_id == friend_id) & (FriendshipRow.friend_id == user_id),
                    )
                )
            )
