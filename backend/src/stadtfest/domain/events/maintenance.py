"""Maintaining events (R07): status machine, publication rules and change tracking.

The rules hold for every entry point (app via REST, MCP, AI drafts): `ManagedEvent` is the
aggregate the moderation use cases load, change and save.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from datetime import date, datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import UUID

from stadtfest.domain.events.event import EventStatus

SHORT_NAME_LENGTH = 18

# Fields a cancelled event still accepts (texts only, R07-US5).
CANCELLED_EDITABLE = frozenset(
    {"description", "opening_hours", "price", "transit", "parking", "website_url", "cancel_reason"}
)


class InvalidTransitionError(Exception):
    """The requested status change or edit is not allowed in the current status."""


class PublicationError(Exception):
    """Required fields for publishing are missing or invalid.

    Attributes:
        problems: Field name (API spelling) -> machine-readable problem code.
    """

    def __init__(self, problems: dict[str, str]) -> None:
        """Create the error."""
        super().__init__(", ".join(problems))
        self.problems = problems


class DomainEventType(StrEnum):
    """Domain events written to the outbox (ADR 0005)."""

    PUBLISHED = "event.published"
    UPDATED = "event.updated"
    UNPUBLISHED = "event.unpublished"
    CANCELLED = "event.cancelled"
    DELETED = "event.deleted"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """A change other parts of the system react to. Carries IDs and field names only."""

    type: DomainEventType
    event_id: UUID
    changed_fields: tuple[str, ...] = ()
    # `event.published` only: the event becomes public for the first time ("near", R11).
    first_publication: bool = False


@dataclass(frozen=True, slots=True)
class ProgramEntry:
    """Program line of an event."""

    date: date
    time_label: str
    title: str
    subtitle: str | None = None


@dataclass(frozen=True, slots=True)
class EventContent:
    """Editable content of an event. Drafts may leave everything but the name empty."""

    name: str
    short_name: str = ""
    category_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    opening_hours: tuple[str, ...] = ()
    price: str | None = None
    place: str = ""
    address: str = ""
    city: str = ""
    postal_code: str | None = None
    lat: float | None = None
    lon: float | None = None
    description: str | None = None
    program: tuple[ProgramEntry, ...] = ()
    transit: str | None = None
    parking: str | None = None
    website_url: str | None = None
    cancel_reason: str | None = None

    def with_defaults(self) -> EventContent:
        """Trim the name and derive a missing short name from it."""
        name = self.name.strip()
        short = (self.short_name or "").strip() or name[:SHORT_NAME_LENGTH].rstrip()
        return replace(self, name=name, short_name=short)


# API spelling of field names, used in `changedFields` and validation responses.
API_FIELD_NAMES = {
    "name": "name",
    "short_name": "shortName",
    "category_id": "categoryId",
    "start_date": "startDate",
    "end_date": "endDate",
    "opening_hours": "openingHours",
    "price": "price",
    "place": "place",
    "address": "address",
    "city": "city",
    "postal_code": "postalCode",
    "lat": "lat",
    "lon": "lon",
    "description": "description",
    "program": "program",
    "transit": "transit",
    "parking": "parking",
    "website_url": "websiteUrl",
    "cancel_reason": "cancelReason",
}


def is_web_url(value: str) -> bool:
    """Whether the value is an absolute http(s) URL with a host."""
    parts = urlsplit(value.strip())
    return parts.scheme in {"http", "https"} and bool(parts.netloc) and " " not in value


def publication_problems(
    content: EventContent, active_category_ids: frozenset[UUID]
) -> dict[str, str]:
    """Check the required fields for publishing (R07-US4).

    Args:
        content: Content to publish.
        active_category_ids: Categories that may be chosen.

    Returns:
        Field name (API spelling) -> problem code; empty if the content may be published.
    """
    problems: dict[str, str] = {}
    if not content.name.strip():
        problems["name"] = "required"
    if content.category_id is None:
        problems["categoryId"] = "required"
    elif content.category_id not in active_category_ids:
        problems["categoryId"] = "inactive"
    if content.start_date is None:
        problems["startDate"] = "required"
    if content.end_date is None:
        problems["endDate"] = "required"
    elif content.start_date is not None and content.end_date < content.start_date:
        problems["endDate"] = "before_start"
    if content.lat is None or content.lon is None:
        problems["location"] = "required"
    if content.website_url and not is_web_url(content.website_url):
        problems["websiteUrl"] = "invalid_url"
    return problems


def changed_fields(before: EventContent, after: EventContent) -> tuple[str, ...]:
    """Names (API spelling) of the fields that differ, in field order."""
    return tuple(
        API_FIELD_NAMES[f.name]
        for f in fields(EventContent)
        if getattr(before, f.name) != getattr(after, f.name)
    )


@dataclass(slots=True)
class ManagedEvent:
    """Event aggregate in the moderation view.

    Status changes return the domain event to record; the caller stores both in one
    transaction (outbox). `version` is the optimistic lock checked when saving.
    """

    id: UUID
    status: EventStatus
    content: EventContent
    version: int = 1
    favorite_count: int = 0
    source: str = "manual"
    # AI finds (R10): the page it came from, the job and when it was found.
    source_url: str | None = None
    ai_job_id: UUID | None = None
    found_at: datetime | None = None
    published_at: datetime | None = None
    deleted: bool = False
    pending_events: list[DomainEvent] = field(default_factory=list)

    def is_past(self, today: date) -> bool:
        """Published events whose end date lies before today count as "past"."""
        return (
            self.status is EventStatus.PUBLISHED
            and self.content.end_date is not None
            and self.content.end_date < today
        )

    def edit(self, content: EventContent) -> None:
        """Replace the content; records `event.updated` for events users can see.

        Raises:
            InvalidTransitionError: If a cancelled event's non-text fields change.
        """
        new = content.with_defaults()
        changes = changed_fields(self.content, new)
        if not changes:
            return
        if self.status is EventStatus.CANCELLED:
            api_editable = {API_FIELD_NAMES[name] for name in CANCELLED_EDITABLE}
            if not set(changes) <= api_editable:
                raise InvalidTransitionError
        self.content = new
        if self.status in {EventStatus.PUBLISHED, EventStatus.CANCELLED}:
            self._record(DomainEventType.UPDATED, changes)

    def publish(self, active_category_ids: frozenset[UUID], now: datetime) -> None:
        """Draft → published.

        Raises:
            InvalidTransitionError: If the event is not a draft.
            PublicationError: If required fields are missing or invalid.
        """
        if self.status is not EventStatus.DRAFT:
            raise InvalidTransitionError
        problems = publication_problems(self.content, active_category_ids)
        if problems:
            raise PublicationError(problems)
        self.status = EventStatus.PUBLISHED
        first = self.published_at is None
        if first:
            self.published_at = now
        self.pending_events.append(
            DomainEvent(DomainEventType.PUBLISHED, self.id, first_publication=first)
        )

    def unpublish(self) -> None:
        """Published → draft (hidden from users, no notification).

        Raises:
            InvalidTransitionError: If the event is not published.
        """
        if self.status is not EventStatus.PUBLISHED:
            raise InvalidTransitionError
        self.status = EventStatus.DRAFT
        self._record(DomainEventType.UNPUBLISHED)

    def cancel(self, reason: str | None) -> None:
        """Published → cancelled; there is no way back (R07-US5).

        Raises:
            InvalidTransitionError: If the event is not published.
        """
        if self.status is not EventStatus.PUBLISHED:
            raise InvalidTransitionError
        self.status = EventStatus.CANCELLED
        cleaned = (reason or "").strip() or None
        self.content = replace(self.content, cancel_reason=cleaned)
        self._record(DomainEventType.CANCELLED)

    def delete(self) -> None:
        """Soft delete from any status."""
        self.deleted = True
        self._record(DomainEventType.DELETED)

    def _record(self, event_type: DomainEventType, changes: tuple[str, ...] = ()) -> None:
        self.pending_events.append(DomainEvent(event_type, self.id, changes))
