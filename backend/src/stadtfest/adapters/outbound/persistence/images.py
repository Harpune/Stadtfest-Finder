"""PostgreSQL implementation of `ImageRepository` (R08)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stadtfest.adapters.outbound.persistence.models import (
    EventImageRow,
    EventRow,
    OutboxRow,
    UploadRow,
)
from stadtfest.application.moderation.image_ports import UploadRecord
from stadtfest.domain.events.images import EventImage, ImageEventType, ImageStatus


def image_from_row(row: EventImageRow) -> EventImage:
    """Domain value of a stored image."""
    return EventImage(
        id=row.id,
        event_id=row.event_id,
        upload_id=row.upload_id,
        position=row.position,
        status=ImageStatus(row.status),
        width=row.width,
        height=row.height,
    )


def _upload_from_row(row: UploadRow) -> UploadRecord:
    return UploadRecord(
        id=row.id,
        user_id=row.user_id,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        created_at=row.created_at,
        consumed_at=row.consumed_at,
    )


async def _write_event(
    session: AsyncSession, event_type: ImageEventType, payload: dict[str, object]
) -> None:
    await session.execute(
        insert(OutboxRow), [{"id": uuid.uuid4(), "type": event_type.value, "payload": payload}]
    )


async def _renumber(session: AsyncSession, event_id: UUID, ordered: Sequence[UUID]) -> None:
    """Set positions 0..n-1; the unique position constraint is checked at commit."""
    if not ordered:
        return
    positions = {image_id: index for index, image_id in enumerate(ordered)}
    await session.execute(
        update(EventImageRow)
        .where(EventImageRow.event_id == event_id, EventImageRow.id.in_(ordered))
        .values(position=case(positions, value=EventImageRow.id))
    )


class SqlImageRepository:
    """Uploads in `upload`, images in `event_image`, events in `outbox` (one transaction)."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Create the repository.

        Args:
            sessions: Session factory of the process.
        """
        self._sessions = sessions

    async def add_upload(self, upload: UploadRecord) -> None:
        """Store a new upload slot."""
        async with self._sessions.begin() as session:
            session.add(
                UploadRow(
                    id=upload.id,
                    user_id=upload.user_id,
                    content_type=upload.content_type,
                    size_bytes=upload.size_bytes,
                    created_at=upload.created_at,
                )
            )

    async def get_upload(self, upload_id: UUID) -> UploadRecord | None:
        """The upload slot, or None."""
        async with self._sessions() as session:
            row = await session.get(UploadRow, upload_id)
        return _upload_from_row(row) if row else None

    async def list_for_event(self, event_id: UUID) -> list[EventImage]:
        """Images of the event ordered by position."""
        async with self._sessions() as session:
            return await self._list(session, event_id)

    @staticmethod
    async def _list(session: AsyncSession, event_id: UUID) -> list[EventImage]:
        rows = await session.scalars(
            select(EventImageRow)
            .where(EventImageRow.event_id == event_id)
            .order_by(EventImageRow.position)
        )
        return [image_from_row(row) for row in rows]

    async def get(self, image_id: UUID) -> EventImage | None:
        """One image, or None."""
        async with self._sessions() as session:
            row = await session.get(EventImageRow, image_id)
        return image_from_row(row) if row else None

    async def attach(self, image: EventImage, consumed_at: datetime) -> None:
        """Insert at the position, consume the upload and write `image.uploaded`."""
        async with self._sessions.begin() as session:
            ordered = [i.id for i in await self._list(session, image.event_id)]
            ordered.insert(image.position, image.id)
            session.add(
                EventImageRow(
                    id=image.id,
                    event_id=image.event_id,
                    upload_id=image.upload_id,
                    position=len(ordered) - 1,
                    status=image.status.value,
                )
            )
            await session.flush()
            await _renumber(session, image.event_id, ordered)
            await session.execute(
                update(UploadRow)
                .where(UploadRow.id == image.upload_id)
                .values(consumed_at=consumed_at)
            )
            await _write_event(
                session,
                ImageEventType.UPLOADED,
                {"imageId": str(image.id), "eventId": str(image.event_id)},
            )

    async def reorder(self, event_id: UUID, image_ids: Sequence[UUID]) -> None:
        """Set positions in the given order."""
        async with self._sessions.begin() as session:
            await _renumber(session, event_id, image_ids)

    async def remove(self, event_id: UUID, image_id: UUID) -> EventImage | None:
        """Delete the image, close the gap and write `image.removed`."""
        async with self._sessions.begin() as session:
            row = await session.get(EventImageRow, image_id, with_for_update=True)
            if row is None or row.event_id != event_id:
                return None
            image = image_from_row(row)
            await session.delete(row)
            await session.flush()
            await _renumber(session, event_id, [i.id for i in await self._list(session, event_id)])
            await _write_event(
                session,
                ImageEventType.REMOVED,
                {
                    "imageId": str(image.id),
                    "eventId": str(event_id),
                    "uploadId": str(image.upload_id) if image.upload_id else None,
                },
            )
            return image

    async def retry(self, image_id: UUID) -> None:
        """Back to processing and write `image.uploaded` again."""
        async with self._sessions.begin() as session:
            event_id = await session.scalar(
                update(EventImageRow)
                .where(EventImageRow.id == image_id)
                .values(status=ImageStatus.PROCESSING.value)
                .returning(EventImageRow.event_id)
            )
            await _write_event(
                session,
                ImageEventType.UPLOADED,
                {"imageId": str(image_id), "eventId": str(event_id)},
            )

    async def mark_ready(self, image_id: UUID, width: int, height: int) -> bool:
        """Mark ready and drop the consumed upload slot (its original is deleted)."""
        async with self._sessions.begin() as session:
            upload_id = await session.scalar(
                select(EventImageRow.upload_id)
                .where(
                    EventImageRow.id == image_id,
                    EventImageRow.status == ImageStatus.PROCESSING.value,
                )
                .with_for_update()
            )
            updated = await session.execute(
                update(EventImageRow)
                .where(
                    EventImageRow.id == image_id,
                    EventImageRow.status == ImageStatus.PROCESSING.value,
                )
                .values(status=ImageStatus.READY.value, width=width, height=height, upload_id=None)
            )
            if updated.rowcount == 0:  # type: ignore[attr-defined]
                return False
            if upload_id is not None:
                await session.execute(delete(UploadRow).where(UploadRow.id == upload_id))
            return True

    async def mark_failed(self, image_id: UUID) -> None:
        """Mark a processing image failed."""
        async with self._sessions.begin() as session:
            await session.execute(
                update(EventImageRow)
                .where(
                    EventImageRow.id == image_id,
                    EventImageRow.status == ImageStatus.PROCESSING.value,
                )
                .values(status=ImageStatus.FAILED.value)
            )

    async def stale_uploads(self, created_before: datetime) -> list[UploadRecord]:
        """Never attached uploads older than the given time."""
        async with self._sessions() as session:
            rows = await session.scalars(
                select(UploadRow).where(
                    UploadRow.consumed_at.is_(None), UploadRow.created_at < created_before
                )
            )
            return [_upload_from_row(row) for row in rows]

    async def delete_uploads(self, upload_ids: Sequence[UUID]) -> None:
        """Delete upload slots."""
        async with self._sessions.begin() as session:
            await session.execute(delete(UploadRow).where(UploadRow.id.in_(upload_ids)))

    async def images_of_deleted_events(self) -> list[EventImage]:
        """Images whose event is soft-deleted."""
        async with self._sessions() as session:
            rows = await session.scalars(
                select(EventImageRow)
                .join(EventRow, EventRow.id == EventImageRow.event_id)
                .where(EventRow.deleted_at.is_not(None))
            )
            return [image_from_row(row) for row in rows]

    async def delete_images(self, image_ids: Sequence[UUID]) -> None:
        """Delete image rows and the upload slots they still reference."""
        async with self._sessions.begin() as session:
            upload_ids = (
                await session.scalars(
                    select(EventImageRow.upload_id).where(
                        EventImageRow.id.in_(image_ids), EventImageRow.upload_id.is_not(None)
                    )
                )
            ).all()
            await session.execute(delete(EventImageRow).where(EventImageRow.id.in_(image_ids)))
            if upload_ids:
                await session.execute(delete(UploadRow).where(UploadRow.id.in_(upload_ids)))
