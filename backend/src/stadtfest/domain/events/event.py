"""Event lifecycle states and public visibility rules."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from stadtfest.domain.events.time_filter import DateRange


class EventStatus(StrEnum):
    """Stored status. "Past" is not stored but derived from the end date."""

    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


PUBLIC_STATUSES = frozenset({EventStatus.PUBLISHED, EventStatus.CANCELLED})


def is_publicly_accessible(status: EventStatus, *, deleted: bool) -> bool:
    """Whether an event may be shown by ID (detail page, timeline, lists).

    Args:
        status: Stored status.
        deleted: Whether the event is soft-deleted.

    Returns:
        True for published or cancelled events that are not deleted, also after they ended.
    """
    return status in PUBLIC_STATUSES and not deleted


def is_listed(status: EventStatus, period: DateRange, today: date, *, deleted: bool) -> bool:
    """Whether an event appears on the map and in the list.

    Args:
        status: Stored status.
        period: Start and end date of the event.
        today: The current day in Europe/Berlin.
        deleted: Whether the event is soft-deleted.

    Returns:
        True for accessible events that have not ended yet.
    """
    return is_publicly_accessible(status, deleted=deleted) and period.end >= today


def is_running(period: DateRange, today: date) -> bool:
    """Whether the event takes place today (start <= today <= end)."""
    return period.contains(today)


def is_past(period: DateRange, today: date) -> bool:
    """Whether the event has ended (end < today)."""
    return period.end < today
