"""Relay and consumers of domain events (ADR 0005).

Consumers are idempotent: bumping a cache generation twice and removing favorites twice
lead to the same state, so at-least-once delivery is safe.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from stadtfest.application.events.use_cases import CATALOG_NAMESPACE
from stadtfest.application.outbox.ports import (
    EventFavorites,
    EventQueue,
    OutboxMessage,
    OutboxStore,
)
from stadtfest.application.shared.ports import CachePort
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


class HandleDomainEvent:
    """Consumers in R07: cache invalidation and clean-up of deleted events."""

    def __init__(self, cache: CachePort, favorites: EventFavorites) -> None:
        """Create the use case."""
        self._cache = cache
        self._favorites = favorites

    async def __call__(self, message: OutboxMessage) -> None:
        """React to one domain event."""
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
