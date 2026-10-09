"""PostgreSQL implementation of the identity ports (user accounts)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import (
    AppUserRow,
    EventRow,
    FavoriteRow,
    ListMemberRow,
    SharedListRow,
)
from stadtfest.application.identity.ports import UserRecord


def _record(row: AppUserRow) -> UserRecord:
    return UserRecord(id=row.id, first_name=row.first_name, last_name=row.last_name)


class SqlUserRepository:
    """User accounts in table `app_user`."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository.

        Args:
            sessions: Session factory.
        """
        self._sessions = sessions

    async def get_or_create(self, subject: str, first_name: str, last_name: str) -> UserRecord:
        """Return the user, inserting it on the first call (race-safe upsert)."""
        async with self._sessions.begin() as session:
            await session.execute(
                insert(AppUserRow)
                .values(
                    id=uuid.uuid4(),
                    idp_subject=subject,
                    first_name=first_name,
                    last_name=last_name,
                )
                .on_conflict_do_nothing(index_elements=[AppUserRow.idp_subject])
            )
            row = await session.scalar(select(AppUserRow).where(AppUserRow.idp_subject == subject))
            assert row is not None  # noqa: S101  # inserted or existing within this transaction
            return _record(row)

    async def update_name(self, subject: str, first_name: str, last_name: str) -> UserRecord | None:
        """Set the names; None if the user does not exist."""
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(AppUserRow)
                .where(AppUserRow.idp_subject == subject)
                .values(first_name=first_name, last_name=last_name, updated_at=func.now())
                .returning(AppUserRow)
            )
            return _record(row) if row is not None else None

    async def delete_personal_data(self, subject: str) -> bool:
        """Delete the user and its personal data in one transaction (Löschkonzept).

        Favorites (R06) are removed by `ON DELETE CASCADE`; their events' counters are
        decremented here first. Notifications, notification settings and devices (R11) go the
        same way, as do friendships, the friend link and notifications naming the user as actor
        (R12). Memberships of shared lists cascade, `created_by` / `added_by` become null and
        lists without members are deleted (R13). Extended by later increments:
        lists (R13), invitations (R14).
        """
        async with self._sessions.begin() as session:
            user_id = await session.scalar(
                select(AppUserRow.id).where(AppUserRow.idp_subject == subject).with_for_update()
            )
            if user_id is None:
                return False
            await session.execute(
                update(EventRow).where(EventRow.created_by == user_id).values(created_by=None)
            )
            await session.execute(
                update(EventRow).where(EventRow.updated_by == user_id).values(updated_by=None)
            )
            favorites = select(FavoriteRow.event_id).where(FavoriteRow.user_id == user_id)
            await session.execute(
                update(EventRow)
                .where(EventRow.id.in_(favorites))
                .values(favorite_count=func.greatest(EventRow.favorite_count - 1, 0))
            )
            await session.delete(await session.get_one(AppUserRow, user_id))
            await session.flush()
            # Memberships went with the account; lists nobody is left in go too (R13).
            await session.execute(
                delete(SharedListRow).where(
                    ~exists().where(ListMemberRow.list_id == SharedListRow.id)
                )
            )
            return True
