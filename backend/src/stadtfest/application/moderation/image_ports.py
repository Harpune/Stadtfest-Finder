"""Outbound ports for event images (R08): object storage, processing, persistence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from stadtfest.domain.events.images import EventImage, ImageFormat, Variant


class StorageUnavailableError(Exception):
    """The object storage cannot be reached or rejected the request."""


class UnsupportedImageError(Exception):
    """The file is not a JPEG, PNG or WebP image (checked by content, not by name)."""


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    """A signed `PUT` URL and the headers the upload must send unchanged."""

    url: str
    headers: Mapping[str, str] = field(default_factory=dict)


class ObjectStorage(Protocol):
    """S3-compatible object storage (ADR 0007)."""

    async def presign_put(
        self, key: str, content_type: str, size_bytes: int, expires_in_seconds: int
    ) -> PresignedUpload:
        """Sign a direct upload of exactly this type and size.

        Raises:
            StorageUnavailableError: If signing is impossible.
        """
        ...

    async def read(self, key: str) -> bytes | None:
        """The object's content, or None if it does not exist.

        Raises:
            StorageUnavailableError: If the storage cannot be reached.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Whether the object exists.

        Raises:
            StorageUnavailableError: If the storage cannot be reached.
        """
        ...

    async def write(self, key: str, data: bytes, content_type: str) -> None:
        """Store an immutable public object (long cache lifetime).

        Raises:
            StorageUnavailableError: If the storage cannot be reached.
        """
        ...

    async def delete(self, keys: Sequence[str]) -> None:
        """Delete objects; unknown keys are ignored.

        Raises:
            StorageUnavailableError: If the storage cannot be reached.
        """
        ...


@dataclass(frozen=True, slots=True)
class ProcessedImage:
    """Variants of an image without any metadata, and the size of the largest one."""

    width: int
    height: int
    files: Mapping[tuple[Variant, ImageFormat], bytes]


class ImageProcessor(Protocol):
    """Checks, strips and scales images."""

    async def process(self, data: bytes) -> ProcessedImage:
        """Create all variants, without EXIF/XMP/ICC text metadata.

        Raises:
            UnsupportedImageError: If the content is no supported image.
        """
        ...


@dataclass(frozen=True, slots=True)
class UploadRecord:
    """A signed upload slot. `consumed_at` is set once it is attached to an event."""

    id: UUID
    user_id: UUID
    content_type: str
    size_bytes: int
    created_at: datetime
    consumed_at: datetime | None = None


class ImageRepository(Protocol):
    """Uploads and event images.

    Changes that other processes react to write `image.*` domain events to the outbox in the
    same transaction (ADR 0005).
    """

    async def add_upload(self, upload: UploadRecord) -> None:
        """Store a new upload slot."""
        ...

    async def get_upload(self, upload_id: UUID) -> UploadRecord | None:
        """The upload slot, or None."""
        ...

    async def list_for_event(self, event_id: UUID) -> list[EventImage]:
        """Images of the event ordered by position."""
        ...

    async def get(self, image_id: UUID) -> EventImage | None:
        """One image, or None."""
        ...

    async def attach(self, image: EventImage, consumed_at: datetime) -> None:
        """Insert the image at its position, consume its upload, write `image.uploaded`.

        Later images move back by one.
        """
        ...

    async def reorder(self, event_id: UUID, image_ids: Sequence[UUID]) -> None:
        """Set positions 0..n-1 in the given order."""
        ...

    async def remove(self, event_id: UUID, image_id: UUID) -> EventImage | None:
        """Delete the image, close the gap and write `image.removed`; None if not found."""
        ...

    async def retry(self, image_id: UUID) -> None:
        """Set the image back to processing and write `image.uploaded` again."""
        ...

    async def mark_ready(self, image_id: UUID, width: int, height: int) -> bool:
        """Mark a processing image ready; False if it no longer exists."""
        ...

    async def mark_failed(self, image_id: UUID) -> None:
        """Mark a processing image failed."""
        ...

    async def stale_uploads(self, created_before: datetime) -> list[UploadRecord]:
        """Uploads that were never attached and are older than the given time."""
        ...

    async def delete_uploads(self, upload_ids: Sequence[UUID]) -> None:
        """Delete upload slots."""
        ...

    async def images_of_deleted_events(self) -> list[EventImage]:
        """Images whose event is soft-deleted."""
        ...

    async def delete_images(self, image_ids: Sequence[UUID]) -> None:
        """Delete image rows (the files are deleted by the caller)."""
        ...
