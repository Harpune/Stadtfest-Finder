"""Notifications: types, triggers, idempotency and texts (R11-US1, US3, US4, E-04, E-09).

A notification is stored structurally (type + IDs); its German text is rendered when it is
read, from the current event data. Push messages only carry generic texts per type and IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")

# API field names (`changedFields` of `event.updated`) that users with a favorite must hear
# about: date, opening hours or place (R11-US4).
CHANGE_TRIGGERS = frozenset({"startDate", "endDate", "openingHours", "address", "lat", "lon"})


class SubjectKind(StrEnum):
    """What a notification is about; the value is the API target type."""

    EVENT = "event"
    PERSON = "friend"
    LIST = "list"


class NotificationType(StrEnum):
    """Types listed in the app; invitations add theirs later (extensible, ADR 0017)."""

    REMIND = "remind"
    NEAR = "near"
    CHANGE = "change"
    CANCEL = "cancel"
    FRIEND_ADDED = "friend_added"
    LIST_ADDED = "list_added"

    @property
    def subject(self) -> SubjectKind:
        """The kind of subject: an event, a person (new friend) or a shared list."""
        match self:
            case NotificationType.FRIEND_ADDED:
                return SubjectKind.PERSON
            case NotificationType.LIST_ADDED:
                return SubjectKind.LIST
            case _:
                return SubjectKind.EVENT


class PushOnlyType(StrEnum):
    """Pushes without a list entry: AI search results for the moderator (R11-US4)."""

    AI_SEARCH_COMPLETED = "ai_search_completed"
    AI_SEARCH_FAILED = "ai_search_failed"


def is_relevant_change(changed_fields: tuple[str, ...] | list[str]) -> bool:
    """Whether an `event.updated` changes date, opening hours or place."""
    return not CHANGE_TRIGGERS.isdisjoint(changed_fields)


def dedupe_key(notification_type: NotificationType, subject_id: UUID, at: datetime) -> str:
    """Idempotency key, unique per user (R11-US3).

    The subject is the event, for `friend_added` the new friend.

    - `remind`: at most one per event and Berlin day
    - `change`: at most one per event and hour, so several edits are combined
    - `near` and `cancel`: once per event (`near` only on the first publication)
    - `friend_added`: once per friend, `list_added`: once per list
    """
    local = at.astimezone(BERLIN)
    match notification_type:
        case NotificationType.REMIND:
            return f"remind:{subject_id}:{local:%Y-%m-%d}"
        case NotificationType.CHANGE:
            return f"change:{subject_id}:{local:%Y-%m-%dT%H}"
        case (
            NotificationType.NEAR
            | NotificationType.CANCEL
            | NotificationType.FRIEND_ADDED
            | NotificationType.LIST_ADDED
        ):
            return f"{notification_type.value}:{subject_id}"


@dataclass(frozen=True, slots=True)
class PushText:
    """Generic title and body of a push: no names, event names or places (E-04)."""

    title: str
    body: str


PUSH_TEXTS: dict[NotificationType | PushOnlyType, PushText] = {
    NotificationType.REMIND: PushText("Erinnerung", "Eines deiner Lieblingsfeste beginnt bald."),
    NotificationType.NEAR: PushText(
        "Neu an deinem Wohnort", "In deiner Nähe gibt es ein neues Fest."
    ),
    NotificationType.CHANGE: PushText(
        "Änderung", "Bei einem deiner Favoriten hat sich etwas geändert."
    ),
    NotificationType.CANCEL: PushText("Fest abgesagt", "Eines deiner Lieblingsfeste fällt aus."),
    # Not pushed (R12), kept for completeness of the generic texts.
    NotificationType.FRIEND_ADDED: PushText("Neuer Freund", "Jemand ist jetzt mit dir befreundet."),
    NotificationType.LIST_ADDED: PushText(
        "Gemeinsame Liste", "Du wurdest zu einer gemeinsamen Liste hinzugefügt."
    ),
    PushOnlyType.AI_SEARCH_COMPLETED: PushText(
        "Suche abgeschlossen", "Die automatische Suche ist fertig."
    ),
    PushOnlyType.AI_SEARCH_FAILED: PushText(
        "Suche fehlgeschlagen", "Die automatische Suche konnte nicht abgeschlossen werden."
    ),
}


@dataclass(frozen=True, slots=True)
class EventFacts:
    """Current public data of the referenced event, read when the list is shown."""

    name: str
    city: str
    start_date: date | None
    end_date: date | None
    cancel_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PersonFacts:
    """Current name of the person a notification is about (e.g. a new friend)."""

    first_name: str
    last_name: str


@dataclass(frozen=True, slots=True)
class ListFacts:
    """Current name of a shared list and the first name of who added the user."""

    list_name: str
    actor_first_name: str


_DASH = "\u2013"  # en dash, as in the app
_LOW, _HIGH = "\u201a", "\u2018"  # German single quotes around list names
_MONTHS = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")


def format_period(start: date | None, end: date | None) -> str:
    """German date range as in the app, e.g. "12.-13. Dez 2026" (with en dashes)."""
    if start is None:
        return "Termin offen"
    end = end or start

    def day_month(day: date) -> str:
        return f"{day.day}. {_MONTHS[day.month - 1]}"

    if start == end:
        return f"{day_month(start)} {start.year}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}.{_DASH}{day_month(end)} {end.year}"
    if start.year == end.year:
        return f"{day_month(start)} {_DASH} {day_month(end)} {end.year}"
    return f"{day_month(start)} {start.year} {_DASH} {day_month(end)} {end.year}"


def _starts_in(days: int) -> str:
    match days:
        case 0:
            return "heute"
        case 1:
            return "morgen"
        case 7:
            return "in einer Woche"
        case _:
            return f"in {days} Tagen"


type Facts = EventFacts | PersonFacts | ListFacts


def render_text(
    notification_type: NotificationType,
    facts: Facts,
    created_at: datetime,
) -> str:
    """The German list text of a notification (E-09)."""
    if isinstance(facts, PersonFacts):
        name = f"{facts.first_name} {facts.last_name}".strip()
        return f"{name} ist jetzt mit dir befreundet."
    if isinstance(facts, ListFacts):
        who = facts.actor_first_name or "Jemand"
        return f"{who} hat dich zur Liste {_LOW}{facts.list_name}{_HIGH} hinzugefügt."
    event = facts
    period = format_period(event.start_date, event.end_date)
    place = f" in {event.city}" if event.city else ""
    match notification_type:
        case NotificationType.REMIND:
            created_on = created_at.astimezone(BERLIN).date()
            days = (event.start_date - created_on).days if event.start_date else 0
            return f"{event.name} beginnt {_starts_in(max(days, 0))}: {period}{place}."
        case NotificationType.NEAR:
            return f"Neu{place}: {event.name} ({period})."
        case NotificationType.CHANGE:
            return (
                f"Bei {event.name} haben sich Termin, Zeiten oder Ort geändert. "
                f"Aktuell: {period}{place}."
            )
        case NotificationType.CANCEL:
            reason = f" Grund: {event.cancel_reason}" if event.cancel_reason else ""
            return f"{event.name} ({period}) fällt aus.{reason}"
        case NotificationType.FRIEND_ADDED | NotificationType.LIST_ADDED:
            raise ValueError(f"{notification_type} needs PersonFacts or ListFacts")
