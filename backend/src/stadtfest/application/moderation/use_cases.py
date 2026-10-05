"""Moderation use cases for events (R07).

Authorization lives here, not in the adapters: only moderators. The role covers all events;
there are no regions (ADR 0015).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, fields, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from stadtfest.application.moderation.ports import (
    AccountResolver,
    ActiveCategories,
    ManagedEventRepository,
    ModEventSummary,
    VersionConflictError,
)
from stadtfest.application.shared.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)
from stadtfest.application.shared.ports import Clock
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.images import EventImage
from stadtfest.domain.events.maintenance import (
    EventContent,
    InvalidTransitionError,
    ManagedEvent,
    PublicationError,
)
from stadtfest.domain.identity.principal import Principal

VERSION_CONFLICT = "version_conflict"
INVALID_TRANSITION = "invalid_transition"

_CONTENT_FIELDS = frozenset(f.name for f in fields(EventContent))


class ModStatus(StrEnum):
    """Status in the moderation view; `past` is derived from the end date."""

    DRAFT = "draft"
    PUBLISHED = "published"
    PAST = "past"
    CANCELLED = "cancelled"


def mod_status(status: EventStatus, end_date: date | None, today: date) -> ModStatus:
    """Derive the status shown to moderators."""
    if status is EventStatus.PUBLISHED and end_date is not None and end_date < today:
        return ModStatus.PAST
    return ModStatus(status.value)


@dataclass(frozen=True, slots=True)
class ModEventView:
    """An event as returned to the moderator, with its derived status and images (R08)."""

    event: ManagedEvent
    status: ModStatus
    images: tuple[EventImage, ...] = ()


@dataclass(frozen=True, slots=True)
class ModEventRow:
    """Overview row with its derived status."""

    summary: ModEventSummary
    status: ModStatus


class _Moderation:
    """Shared authorization: the moderator role."""

    def __init__(self, events: ManagedEventRepository, clock: Clock) -> None:
        self._events = events
        self._clock = clock

    @staticmethod
    def _authorize(principal: Principal) -> None:
        if not principal.can_moderate:
            raise ForbiddenError

    async def _event(self, principal: Principal, event_id: UUID) -> ManagedEvent:
        self._authorize(principal)
        event = await self._events.get(event_id)
        if event is None:
            raise NotFoundError
        return event

    async def _view(self, event: ManagedEvent, *, with_images: bool = True) -> ModEventView:
        images = tuple(await self._events.list_images(event.id)) if with_images else ()
        return ModEventView(
            event, mod_status(event.status, event.content.end_date, self._clock.today()), images
        )


class ListModEvents(_Moderation):
    """Overview of all events (R07-US2)."""

    async def __call__(
        self,
        principal: Principal,
        *,
        status: ModStatus | None = None,
        query: str | None = None,
        ids: frozenset[UUID] | None = None,
    ) -> list[ModEventRow]:
        """Return the events: upcoming ascending, then past descending, then undated."""
        self._authorize(principal)
        today = self._clock.today()
        rows = [
            ModEventRow(item, mod_status(item.status, item.end_date, today))
            for item in await self._events.list_events(ids)
        ]
        if status is not None:
            rows = [row for row in rows if row.status is status]
        if query:
            needle = query.casefold()
            rows = [
                row
                for row in rows
                if needle in f"{row.summary.name} {row.summary.place} {row.summary.city}".casefold()
            ]
        return sorted(rows, key=lambda row: _overview_order(row.summary, today))


def _overview_order(item: ModEventSummary, today: date) -> tuple[int, int, str]:
    if item.start_date is None or item.end_date is None:
        return (2, 0, item.name)
    if item.end_date >= today:
        return (0, item.start_date.toordinal(), item.name)
    return (1, -item.start_date.toordinal(), item.name)


class GetModEvent(_Moderation):
    """One event for editing."""

    async def __call__(self, principal: Principal, event_id: UUID) -> ModEventView:
        """Return the event."""
        event = await self._event(principal, event_id)
        return await self._view(event)


class CreateModEvent(_Moderation):
    """Create a draft (R07-US3)."""

    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        accounts: AccountResolver,
    ) -> None:
        """Create the use case."""
        super().__init__(events, clock)
        self._accounts = accounts

    async def __call__(self, principal: Principal, content: EventContent) -> ModEventView:
        """Store the content as a new draft; only the name is required."""
        self._authorize(principal)
        content = content.with_defaults()
        if not content.name:
            raise InvalidInputError({"name": "required"})
        event = ManagedEvent(uuid4(), EventStatus.DRAFT, content)
        await self._events.add(event, await self._accounts(principal))
        return await self._view(event, with_images=False)


class _Changing(_Moderation):
    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        accounts: AccountResolver,
    ) -> None:
        super().__init__(events, clock)
        self._accounts = accounts

    async def _store(
        self, principal: Principal, event: ManagedEvent, expected_version: int
    ) -> ModEventView:
        try:
            event.version = await self._events.save(
                event, expected_version, await self._accounts(principal)
            )
        except VersionConflictError:
            raise ConflictError(VERSION_CONFLICT) from None
        return await self._view(event)


class UpdateModEvent(_Changing):
    """Merge-patch an event under the optimistic lock (R07-US3)."""

    async def __call__(
        self,
        principal: Principal,
        event_id: UUID,
        changes: Mapping[str, object],
        expected_version: int,
    ) -> ModEventView:
        """Apply the present fields; `program` replaces the whole program.

        Raises:
            ConflictError: `version_conflict` or `invalid_transition` (cancelled events).
        """
        event = await self._event(principal, event_id)
        if event.version != expected_version:
            raise ConflictError(VERSION_CONFLICT)
        unknown = set(changes) - _CONTENT_FIELDS
        if unknown:
            raise InvalidInputError(dict.fromkeys(sorted(unknown), "unknown_field"))
        content = replace(event.content, **changes)  # type: ignore[arg-type]
        if not content.name.strip():
            raise InvalidInputError({"name": "required"})
        try:
            event.edit(content)
        except InvalidTransitionError:
            raise ConflictError(INVALID_TRANSITION) from None
        return await self._store(principal, event, expected_version)


class PublishModEvent(_Changing):
    """Draft → published, with the required fields check (R07-US4)."""

    def __init__(
        self,
        events: ManagedEventRepository,
        clock: Clock,
        accounts: AccountResolver,
        categories: ActiveCategories,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Create the use case."""
        super().__init__(events, clock, accounts)
        self._categories = categories
        self._now = now

    async def __call__(self, principal: Principal, event_id: UUID) -> ModEventView:
        """Publish the draft.

        Raises:
            InvalidInputError: `validation_failed` with fields.
            ConflictError: `invalid_transition` if the event is no draft.
        """
        event = await self._event(principal, event_id)
        version = event.version
        try:
            event.publish(await self._categories.active_ids(), self._now())
        except InvalidTransitionError:
            raise ConflictError(INVALID_TRANSITION) from None
        except PublicationError as error:
            raise InvalidInputError(error.problems) from None
        return await self._store(principal, event, version)


class UnpublishModEvent(_Changing):
    """Published → draft (R07-US5)."""

    async def __call__(self, principal: Principal, event_id: UUID) -> ModEventView:
        """Withdraw the event.

        Raises:
            ConflictError: `invalid_transition` if the event is not published.
        """
        event = await self._event(principal, event_id)
        version = event.version
        try:
            event.unpublish()
        except InvalidTransitionError:
            raise ConflictError(INVALID_TRANSITION) from None
        return await self._store(principal, event, version)


class CancelModEvent(_Changing):
    """Published → cancelled (R07-US5)."""

    async def __call__(
        self, principal: Principal, event_id: UUID, reason: str | None
    ) -> ModEventView:
        """Cancel the event; the reason is shown in the notification (R11).

        Raises:
            ConflictError: `invalid_transition` if the event is not published.
        """
        event = await self._event(principal, event_id)
        version = event.version
        try:
            event.cancel(reason)
        except InvalidTransitionError:
            raise ConflictError(INVALID_TRANSITION) from None
        return await self._store(principal, event, version)


class DeleteModEvent(_Changing):
    """Soft delete from any status (R07-US5)."""

    async def __call__(self, principal: Principal, event_id: UUID) -> None:
        """Delete the event; favorites are removed by the `event.deleted` consumer."""
        event = await self._event(principal, event_id)
        version = event.version
        event.delete()
        await self._store(principal, event, version)
