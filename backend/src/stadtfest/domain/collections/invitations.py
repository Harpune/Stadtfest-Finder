"""Invitations to an event (R14): rules for inviting, answering and reminding."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum

MESSAGE_MAX = 280
INVITEES_MAX = 50
REMINDER_INTERVAL = timedelta(hours=24)
# Invitations are deleted this long after the event ended (Löschkonzept, assumption).
RETENTION = timedelta(days=183)
EVENT_NOT_INVITABLE = "event_not_invitable"


class InviteeStatus(StrEnum):
    """Answer of an invitee."""

    OPEN = "open"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class InvitationEventType(StrEnum):
    """Domain events of invitations (outbox, ADR 0005); payloads carry IDs only."""

    INVITEES_ADDED = "invitation.invitees_added"
    REMINDED = "invitation.reminded"
    RESPONDED = "invitation.responded"


def is_invitable(status: str, end_date: date | None, today: date) -> bool:
    """Only published events that have not ended can be invited to (and answered)."""
    return status == "published" and end_date is not None and end_date >= today


def clean_message(message: str | None) -> str | None:
    """The trimmed message, None if empty.

    Raises:
        ValueError: If it is longer than `MESSAGE_MAX`.
    """
    if message is None:
        return None
    cleaned = message.strip()
    if len(cleaned) > MESSAGE_MAX:
        raise ValueError("message too long")
    return cleaned or None


def reminder_wait(last_reminder_at: datetime | None, now: datetime) -> timedelta | None:
    """How long the host has to wait before reminding again, None if allowed now."""
    if last_reminder_at is None:
        return None
    wait = last_reminder_at + REMINDER_INTERVAL - now
    return wait if wait > timedelta(0) else None
