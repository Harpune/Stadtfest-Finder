"""Relay and consumers of domain events (ADR 0005).

Consumers are idempotent: bumping a cache generation twice and removing favorites twice
lead to the same state, so at-least-once delivery is safe.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

from stadtfest.application.events.use_cases import CATALOG_NAMESPACE, CATEGORIES_NAMESPACE
from stadtfest.application.outbox.ports import (
    EventFavorites,
    EventQueue,
    OutboxMessage,
    OutboxStore,
)
from stadtfest.application.shared.ports import CachePort
from stadtfest.domain.ai_ingestion.job import AiSearchEventType
from stadtfest.domain.events.category import CATEGORY_CHANGED
from stadtfest.domain.events.images import ImageEventType
from stadtfest.domain.events.maintenance import DomainEventType

logger = logging.getLogger(__name__)

RELAY_BATCH = 100
RETENTION = timedelta(days=14)

# Events that change what users see: the cached public search must be invalidated.
_CATALOG_CHANGES = frozenset(DomainEventType)


class RelayOutbox:
    """Moves pending outbox messages into the job queue (runs every second in the worker)."""

    def __init__(self, outbox: OutboxStore, queue: EventQueue) -> None:
        """Create the use case."""
        self._outbox = outbox
        self._queue = queue

    async def __call__(self) -> int:
        """Relay one batch; returns the number of relayed messages."""
        return await self._outbox.dispatch_pending(RELAY_BATCH, self._queue.enqueue_domain_event)


ProcessImageHandler = Callable[[UUID], Awaitable[object]]
RunAiSearchHandler = Callable[[UUID], Awaitable[object]]
DeleteImageFilesHandler = Callable[[UUID, UUID | None], Awaitable[None]]
NotifyHandler = Callable[[str, Mapping[str, object]], Awaitable[object]]


class HandleDomainEvent:
    """Consumers: caches (R07), images (R08), categories (R09), AI (R10), notifications (R11)."""

    def __init__(
        self,
        cache: CachePort,
        favorites: EventFavorites,
        process_image: ProcessImageHandler,
        delete_image_files: DeleteImageFilesHandler,
        run_ai_search: RunAiSearchHandler | None = None,
        notify: NotifyHandler | None = None,
    ) -> None:
        """Create the use case."""
        self._cache = cache
        self._favorites = favorites
        self._process_image = process_image
        self._delete_image_files = delete_image_files
        self._run_ai_search = run_ai_search
        self._notify = notify

    async def __call__(self, message: OutboxMessage) -> None:
        """React to one domain event."""
        if message.type == AiSearchEventType.REQUESTED.value:
            if self._run_ai_search is not None:
                await self._run_ai_search(UUID(str(message.payload["jobId"])))
            return
        if message.type in {AiSearchEventType.COMPLETED.value, AiSearchEventType.FAILED.value}:
            # Push to the moderator who started the search (E-12, R11).
            if self._notify is not None:
                await self._notify(message.type, message.payload)
            return
        if message.type == CATEGORY_CHANGED:
            # Chips (public list, ETag) and catalog counts/filters follow (R09-US5).
            await self._cache.bump_generation(CATEGORIES_NAMESPACE)
            await self._cache.bump_generation(CATALOG_NAMESPACE)
            return
        if message.type in set(ImageEventType):
            await self._handle_image(ImageEventType(message.type), message.payload)
            return
        try:
            event_type = DomainEventType(message.type)
        except ValueError:
            logger.warning("unknown_domain_event", extra={"event_type": message.type})
            return
        if event_type in _CATALOG_CHANGES:
            await self._cache.bump_generation(CATALOG_NAMESPACE)
        if event_type is DomainEventType.DELETED:
            # `favorite_count` stays as historical value (R07-US7).
            await self._favorites.remove_for_event(UUID(str(message.payload["eventId"])))
        elif self._notify is not None:
            # "near", "change" and "cancel" (R11-US4); the consumer ignores other types.
            await self._notify(message.type, message.payload)

    async def _handle_image(self, event_type: ImageEventType, payload: dict[str, object]) -> None:
        image_id = UUID(str(payload["imageId"]))
        if event_type is ImageEventType.UPLOADED:
            await self._process_image(image_id)
        else:
            upload_id = payload.get("uploadId")
            await self._delete_image_files(image_id, UUID(str(upload_id)) if upload_id else None)


class PurgeOutbox:
    """Deletes dispatched messages after 14 days (daily job)."""

    def __init__(
        self, outbox: OutboxStore, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        """Create the use case."""
        self._outbox = outbox
        self._now = now

    async def __call__(self) -> int:
        """Delete old dispatched messages; returns the number deleted."""
        return await self._outbox.purge_dispatched(self._now() - RETENTION)
