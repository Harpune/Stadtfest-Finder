"""Outbound ports of the moderation context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.images import EventImage
from stadtfest.domain.events.maintenance import ManagedEvent
from stadtfest.domain.identity.principal import Principal


class VersionConflictError(Exception):
    """The event was changed since the caller loaded it (optimistic lock)."""


@dataclass(frozen=True, slots=True)
class ModEventSummary:
    """Row of the moderation overview."""

    id: UUID
    name: str
    status: EventStatus
    start_date: date | None
    end_date: date | None
    place: str
    city: str
    category_id: UUID | None
    favorite_count: int
    source: str
    version: int


class ManagedEventRepository(Protocol):
    """Events as maintained by moderators.

    Saving writes pending domain events to the outbox in the same transaction (ADR 0005).
    """

    async def list_events(self, ids: frozenset[UUID] | None) -> list[ModEventSummary]:
        """All non-deleted events, optionally restricted to `ids`."""
        ...

    async def get(self, event_id: UUID) -> ManagedEvent | None:
        """The event with its program, or None if unknown or deleted."""
        ...

    async def list_images(self, event_id: UUID) -> list[EventImage]:
        """The event's images ordered by position (R08)."""
        ...

    async def add(self, event: ManagedEvent, user_id: UUID) -> None:
        """Insert a new event (version 1) and its pending domain events."""
        ...

    async def save(self, event: ManagedEvent, expected_version: int, user_id: UUID) -> int:
        """Store the changes if the stored version still matches.

        Returns:
            The new version.

        Raises:
            VersionConflictError: If the event was changed or deleted meanwhile.
        """
        ...


class ActiveCategories(Protocol):
    """Categories that may be chosen for an event."""

    async def active_ids(self) -> frozenset[UUID]:
        """IDs of the active categories."""
        ...


class AccountResolver(Protocol):
    """Makes sure the caller has an account (identity context) and returns its ID."""

    async def __call__(self, principal: Principal) -> UUID:
        """Create the account on first use and return the user ID (audit fields)."""
        ...
