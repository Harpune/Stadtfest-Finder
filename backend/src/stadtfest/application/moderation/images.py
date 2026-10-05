"""Use cases for event images (R08).

Moderator actions share the authorization of the event use cases (moderator role).
Processing and clean-up run in the worker, triggered by `image.*` domain events.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from stadtfest.application.events.use_cases import CATALOG_NAMESPACE
from stadtfest.application.moderation.image_ports import (
    ImageProcessor,
    ImageRepository,
    ObjectStorage,
    StorageUnavailableError,
    UnsupportedImageError,
    UploadRecord,
)
from stadtfest.application.moderation.ports import (
    AccountResolver,
    ManagedEventRepository,
)
from stadtfest.application.moderation.use_cases import _Moderation
from stadtfest.application.shared.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)
from stadtfest.application.shared.ports import CachePort, Clock
from stadtfest.domain.events.images import (
    EventImage,
    ImageFormat,
    ImageStatus,
    InvalidOrderError,
    TooManyImagesError,
    all_variant_keys,
    check_order,
    insert_position,
    upload_key,
    upload_problems,
    variant_key,
)
from stadtfest.domain.identity.principal import Principal

logger = logging.getLogger(__name__)

UPLOAD_URL_LIFETIME = timedelta(minutes=10)
STALE_UPLOAD_AGE = timedelta(hours=24)
STORAGE_UNAVAILABLE = "storage_unavailable"
INVALID_UPLOAD = "invalid_upload"
TOO_MANY_IMAGES = "too_many_images"
NOT_RETRYABLE = "not_retryable"

_CONTENT_TYPES = {ImageFormat.WEBP: "image/webp", ImageFormat.JPEG: "image/jpeg"}

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class UploadSlot:
    """Where and how the app uploads the file."""

    upload_id: UUID
    url: str
    headers: dict[str, str]
    expires_at: datetime


class _ImageModeration(_Moderation):
    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        images: ImageRepository,
        cache: CachePort,
    ) -> None:
        super().__init__(events, clock)
        self._images = images
        self._cache = cache

    async def _images_changed(self) -> None:
        # Cover and gallery are part of the cached public catalog.
        await self._cache.bump_generation(CATALOG_NAMESPACE)


class CreateUpload(_Moderation):
    """Sign a direct upload into the object storage (R08-US1)."""

    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        accounts: AccountResolver,
        images: ImageRepository,
        storage: ObjectStorage,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        super().__init__(events, clock)
        self._accounts = accounts
        self._images = images
        self._storage = storage
        self._now = now

    async def __call__(
        self, principal: Principal, content_type: str, size_bytes: int
    ) -> UploadSlot:
        """Return a signed PUT URL valid for 10 minutes.

        Raises:
            InvalidInputError: Type or size not allowed.
            ServiceUnavailableError: The storage cannot sign the URL.
        """
        self._authorize(principal)
        problems = upload_problems(content_type, size_bytes)
        if problems:
            raise InvalidInputError(problems)
        upload = UploadRecord(
            uuid4(), await self._accounts(principal), content_type, size_bytes, self._now()
        )
        try:
            signed = await self._storage.presign_put(
                upload_key(upload.id), content_type, int(UPLOAD_URL_LIFETIME.total_seconds())
            )
        except StorageUnavailableError:
            raise ServiceUnavailableError(STORAGE_UNAVAILABLE) from None
        await self._images.add_upload(upload)
        return UploadSlot(
            upload.id, signed.url, dict(signed.headers), upload.created_at + UPLOAD_URL_LIFETIME
        )


class AttachImage(_ImageModeration):
    """Attach an uploaded file to an event; processing follows in the worker (R08-US1)."""

    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        images: ImageRepository,
        cache: CachePort,
        accounts: AccountResolver,
        storage: ObjectStorage,
        now: Now = _utc_now,
    ) -> None:
        """Create the use case."""
        super().__init__(events, clock, images, cache)
        self._accounts = accounts
        self._storage = storage
        self._now = now

    async def __call__(
        self, principal: Principal, event_id: UUID, upload_id: UUID, position: int | None
    ) -> EventImage:
        """Attach the upload at the position (appended by default).

        Raises:
            InvalidInputError: `invalid_upload` or `too_many_images`.
            ServiceUnavailableError: The storage cannot be reached.
        """
        event = await self._event(principal, event_id)
        upload = await self._images.get_upload(upload_id)
        if (
            upload is None
            or upload.consumed_at is not None
            or upload.user_id != await self._accounts(principal)
            or await self._uploaded_size(upload.id) != upload.size_bytes
        ):
            raise InvalidInputError({"uploadId": INVALID_UPLOAD}, INVALID_UPLOAD)
        current = await self._images.list_for_event(event.id)
        try:
            index = insert_position(len(current), position)
        except TooManyImagesError:
            raise InvalidInputError({"images": TOO_MANY_IMAGES}, TOO_MANY_IMAGES) from None
        image = EventImage(uuid4(), event.id, upload.id, index, ImageStatus.PROCESSING)
        await self._images.attach(image, self._now())
        return image

    async def _uploaded_size(self, upload_id: UUID) -> int | None:
        # The declared size is the limit: the signed URL does not enforce it (see port).
        try:
            return await self._storage.size(upload_key(upload_id))
        except StorageUnavailableError:
            raise ServiceUnavailableError(STORAGE_UNAVAILABLE) from None


class OrderImages(_ImageModeration):
    """Set the order; the first image is the cover (R08-US3)."""

    async def __call__(
        self, principal: Principal, event_id: UUID, image_ids: Sequence[UUID]
    ) -> list[EventImage]:
        """Apply the complete new order.

        Raises:
            InvalidInputError: An ID is missing, unknown or repeated.
        """
        event = await self._event(principal, event_id)
        current = await self._images.list_for_event(event.id)
        try:
            check_order([image.id for image in current], image_ids)
        except InvalidOrderError:
            raise InvalidInputError({"imageIds": "invalid_order"}) from None
        await self._images.reorder(event.id, image_ids)
        await self._images_changed()
        return await self._images.list_for_event(event.id)


class RemoveImage(_ImageModeration):
    """Remove an image at once; the files follow via `image.removed` (R08-US3)."""

    async def __call__(self, principal: Principal, event_id: UUID, image_id: UUID) -> None:
        """Remove the image.

        Raises:
            NotFoundError: The image does not belong to the event.
        """
        event = await self._event(principal, event_id)
        if await self._images.remove(event.id, image_id) is None:
            raise NotFoundError
        await self._images_changed()


class RetryImage(_ImageModeration):
    """Process a failed image again (form tile "Erneut versuchen", R08-US2)."""

    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        images: ImageRepository,
        cache: CachePort,
        storage: ObjectStorage,
    ) -> None:
        """Create the use case."""
        super().__init__(events, clock, images, cache)
        self._storage = storage

    async def __call__(self, principal: Principal, event_id: UUID, image_id: UUID) -> EventImage:
        """Queue the image for processing again.

        Raises:
            NotFoundError: The image does not belong to the event.
            ConflictError: `not_retryable` if it did not fail or its upload is gone.
        """
        event = await self._event(principal, event_id)
        image = await self._images.get(image_id)
        if image is None or image.event_id != event.id:
            raise NotFoundError
        if image.status is not ImageStatus.FAILED or image.upload_id is None:
            raise ConflictError(NOT_RETRYABLE)
        try:
            uploaded = await self._storage.size(upload_key(image.upload_id)) is not None
        except StorageUnavailableError:
            raise ServiceUnavailableError(STORAGE_UNAVAILABLE) from None
        if not uploaded:
            raise ConflictError(NOT_RETRYABLE)
        await self._images.retry(image.id)
        return EventImage(
            image.id, image.event_id, image.upload_id, image.position, ImageStatus.PROCESSING
        )


class ProcessImage:
    """Worker: check the type, strip metadata, create variants, delete the original (R08-US2).

    Idempotent: an image that is no longer processing is skipped.
    """

    def __init__(
        self,
        images: ImageRepository,
        storage: ObjectStorage,
        processor: ImageProcessor,
        cache: CachePort,
    ) -> None:
        """Create the use case."""
        self._images = images
        self._storage = storage
        self._processor = processor
        self._cache = cache

    async def __call__(self, image_id: UUID) -> ImageStatus | None:
        """Process the image; returns the new status, or None if there was nothing to do."""
        image = await self._images.get(image_id)
        if image is None or image.status is not ImageStatus.PROCESSING or image.upload_id is None:
            return None
        original = upload_key(image.upload_id)
        try:
            data = await self._storage.read(original)
            if data is None:
                return await self._fail(image_id, "image_original_missing")
            processed = await self._processor.process(data)
            for (variant, image_format), content in processed.files.items():
                await self._storage.write(
                    variant_key(image.id, variant, image_format),
                    content,
                    _CONTENT_TYPES[image_format],
                )
        except UnsupportedImageError:
            return await self._fail(image_id, "image_unsupported")
        except StorageUnavailableError:
            return await self._fail(image_id, "image_storage_unavailable")
        if not await self._images.mark_ready(image_id, processed.width, processed.height):
            # Removed while processing: the `image.removed` consumer may have run already.
            await self._delete_quietly([*all_variant_keys(image_id), original])
            return None
        await self._delete_quietly([original])
        await self._cache.bump_generation(CATALOG_NAMESPACE)
        return ImageStatus.READY

    async def _fail(self, image_id: UUID, reason: str) -> ImageStatus:
        logger.warning(reason, extra={"image_id": str(image_id)})
        await self._images.mark_failed(image_id)
        return ImageStatus.FAILED

    async def _delete_quietly(self, keys: list[str]) -> None:
        try:
            await self._storage.delete(keys)
        except StorageUnavailableError:
            # The daily clean-up does not find these keys again; log for operators.
            logger.warning("image_files_not_deleted", extra={"count": len(keys)})


class DeleteImageFiles:
    """Worker: delete all files of a removed image (consumer of `image.removed`)."""

    def __init__(self, storage: ObjectStorage) -> None:
        """Create the use case."""
        self._storage = storage

    async def __call__(self, image_id: UUID, upload_id: UUID | None) -> None:
        """Delete variants and original (idempotent).

        Raises:
            StorageUnavailableError: To let the job be retried.
        """
        keys = all_variant_keys(image_id)
        if upload_id is not None:
            keys.append(upload_key(upload_id))
        await self._storage.delete(keys)


@dataclass(frozen=True, slots=True)
class PurgeResult:
    """What the daily clean-up removed."""

    uploads: int
    images: int


class PurgeImages:
    """Daily: stale uploads (> 24 h, never attached) and images of deleted events (R08-US5)."""

    def __init__(
        self, images: ImageRepository, storage: ObjectStorage, now: Now = _utc_now
    ) -> None:
        """Create the use case."""
        self._images = images
        self._storage = storage
        self._now = now

    async def __call__(self) -> PurgeResult:
        """Delete the files first, then the rows, so a failure leaves nothing unreachable."""
        uploads = await self._images.stale_uploads(self._now() - STALE_UPLOAD_AGE)
        if uploads:
            await self._storage.delete([upload_key(upload.id) for upload in uploads])
            await self._images.delete_uploads([upload.id for upload in uploads])
        images = await self._images.images_of_deleted_events()
        if images:
            keys: list[str] = []
            for image in images:
                keys.extend(all_variant_keys(image.id))
                if image.upload_id is not None:
                    keys.append(upload_key(image.upload_id))
            await self._storage.delete(keys)
            await self._images.delete_images([image.id for image in images])
        return PurgeResult(len(uploads), len(images))
