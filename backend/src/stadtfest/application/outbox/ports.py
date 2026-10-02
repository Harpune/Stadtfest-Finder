"""Outbound ports for relaying and consuming domain events."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """A stored domain event. The payload carries IDs and field names only."""

    id: UUID
    type: str
    payload: dict[str, object] = field(default_factory=dict)


class OutboxStore(Protocol):
    """The outbox table."""

    async def dispatch_pending(
        self, limit: int, send: Callable[[OutboxMessage], Awaitable[None]]
    ) -> int:
        """Pass up to `limit` undispatched messages to `send` and mark them dispatched.

        Messages are locked while sending, so parallel relays never pick the same one.
        If marking fails after sending, a message is sent again (at least once).

        Returns:
            Number of dispatched messages.
        """
        ...

    async def purge_dispatched(self, before: datetime) -> int:
        """Delete messages dispatched before the given time; returns the number deleted."""
        ...


class EventQueue(Protocol):
    """Queue for consuming domain events in the worker."""

    async def enqueue_domain_event(self, message: OutboxMessage) -> None:
        """Enqueue the message once (the job ID is derived from the message ID)."""
        ...


class EventFavorites(Protocol):
    """Favorites of an event (collections context)."""

    async def remove_for_event(self, event_id: UUID) -> int:
        """Remove all favorites of the event; returns the number removed."""
        ...
