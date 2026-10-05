from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.maintenance import (
    DomainEventType,
    EventContent,
    InvalidTransitionError,
    ManagedEvent,
    PublicationError,
    changed_fields,
    is_web_url,
    publication_problems,
)

CATEGORY = uuid4()
NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
COMPLETE = EventContent(
    name="Stadtfest Schwäbisch Gmünd",
    category_id=CATEGORY,
    start_date=date(2026, 10, 3),
    end_date=date(2026, 10, 4),
    place="Marktplatz",
    address="Marktplatz",
    city="Schwäbisch Gmünd",
    postal_code="73525",
    lat=48.7996,
    lon=9.7986,
    website_url="https://schwaebisch-gmuend.de",
)


def _event(status: EventStatus = EventStatus.DRAFT, **content: object) -> ManagedEvent:
    return ManagedEvent(uuid4(), status, replace(COMPLETE, **content).with_defaults())


def _types(event: ManagedEvent) -> list[DomainEventType]:
    return [e.type for e in event.pending_events]


# --- publication rules -----------------------------------------------------------------


def test_complete_content_can_be_published() -> None:
    assert publication_problems(COMPLETE, frozenset({CATEGORY})) == {}


@pytest.mark.parametrize(
    ("changes", "field", "problem"),
    [
        ({"name": "  "}, "name", "required"),
        ({"category_id": None}, "categoryId", "required"),
        ({"category_id": uuid4()}, "categoryId", "inactive"),
        ({"start_date": None}, "startDate", "required"),
        ({"end_date": None}, "endDate", "required"),
        ({"end_date": date(2026, 10, 2)}, "endDate", "before_start"),
        ({"lat": None}, "location", "required"),
        ({"lon": None}, "location", "required"),
        ({"website_url": "schwaebisch gmuend"}, "websiteUrl", "invalid_url"),
        ({"website_url": "ftp://example.test"}, "websiteUrl", "invalid_url"),
    ],
)
def test_publication_problems(changes: dict[str, object], field: str, problem: str) -> None:
    content = replace(COMPLETE, **changes)  # type: ignore[arg-type]
    assert publication_problems(content, frozenset({CATEGORY})) == {field: problem}


def test_empty_draft_lists_every_problem() -> None:
    problems = publication_problems(EventContent(name=""), frozenset())
    assert set(problems) == {"name", "categoryId", "startDate", "endDate", "location"}


@pytest.mark.parametrize(
    ("url", "valid"),
    [("https://a.de", True), ("http://a.de/x", True), ("a.de", False), ("javascript:x", False)],
)
def test_is_web_url(url: str, valid: bool) -> None:
    assert is_web_url(url) is valid


def test_short_name_defaults_to_the_shortened_name() -> None:
    content = EventContent(name="  Reichsstädter Tage Aalen 2026  ").with_defaults()
    assert content.name == "Reichsstädter Tage Aalen 2026"
    assert content.short_name == "Reichsstädter Tage"


# --- status machine ----------------------------------------------------------------------


def test_publish_draft() -> None:
    event = _event()
    event.publish(frozenset({CATEGORY}), NOW)
    assert event.status is EventStatus.PUBLISHED
    assert event.published_at == NOW
    assert _types(event) == [DomainEventType.PUBLISHED]


def test_publishing_again_keeps_the_first_publication_time() -> None:
    event = _event()
    event.publish(frozenset({CATEGORY}), NOW)
    event.unpublish()
    event.publish(frozenset({CATEGORY}), datetime(2026, 11, 1, tzinfo=UTC))
    assert event.published_at == NOW
    # Only the first publication announces the event near users' homes (R11).
    published = [e for e in event.pending_events if e.type is DomainEventType.PUBLISHED]
    assert [e.first_publication for e in published] == [True, False]


def test_publish_reports_missing_fields() -> None:
    event = _event(category_id=None, start_date=None)
    with pytest.raises(PublicationError) as raised:
        event.publish(frozenset({CATEGORY}), NOW)
    assert raised.value.problems == {"categoryId": "required", "startDate": "required"}
    assert event.status is EventStatus.DRAFT
    assert event.pending_events == []


@pytest.mark.parametrize("postal_code", ["89073", "10115", None])
def test_publish_anywhere_in_germany(postal_code: str | None) -> None:
    """No regions (ADR 0015): the location is required, not a postal code range."""
    event = _event(postal_code=postal_code)
    event.publish(frozenset({CATEGORY}), NOW)
    assert event.status is EventStatus.PUBLISHED


@pytest.mark.parametrize(
    ("status", "action"),
    [
        (EventStatus.PUBLISHED, "publish"),
        (EventStatus.CANCELLED, "publish"),
        (EventStatus.DRAFT, "unpublish"),
        (EventStatus.CANCELLED, "unpublish"),
        (EventStatus.DRAFT, "cancel"),
        (EventStatus.CANCELLED, "cancel"),
    ],
)
def test_forbidden_transitions(status: EventStatus, action: str) -> None:
    event = _event(status)
    actions = {
        "publish": lambda: event.publish(frozenset({CATEGORY}), NOW),
        "unpublish": event.unpublish,
        "cancel": lambda: event.cancel(None),
    }
    with pytest.raises(InvalidTransitionError):
        actions[action]()


def test_unpublish_and_cancel() -> None:
    withdrawn = _event(EventStatus.PUBLISHED)
    withdrawn.unpublish()
    assert withdrawn.status is EventStatus.DRAFT
    assert _types(withdrawn) == [DomainEventType.UNPUBLISHED]

    cancelled = _event(EventStatus.PUBLISHED)
    cancelled.cancel("  Unwetter  ")
    assert cancelled.status is EventStatus.CANCELLED
    assert cancelled.content.cancel_reason == "Unwetter"
    assert _types(cancelled) == [DomainEventType.CANCELLED]


@pytest.mark.parametrize("status", list(EventStatus))
def test_delete_from_any_status(status: EventStatus) -> None:
    event = _event(status)
    event.delete()
    assert event.deleted
    assert _types(event) == [DomainEventType.DELETED]


def test_past_is_derived_for_published_events() -> None:
    ended = _event(EventStatus.PUBLISHED, end_date=date(2026, 10, 4))
    assert ended.is_past(date(2026, 10, 5))
    assert not ended.is_past(date(2026, 10, 4))
    assert not _event(EventStatus.CANCELLED).is_past(date(2027, 1, 1))


# --- editing -----------------------------------------------------------------------------


def test_editing_a_draft_records_no_event() -> None:
    event = _event()
    event.edit(replace(event.content, description="Neu"))
    assert event.content.description == "Neu"
    assert event.pending_events == []


def test_editing_a_published_event_records_the_changed_fields() -> None:
    event = _event(EventStatus.PUBLISHED)
    event.edit(replace(event.content, start_date=date(2026, 10, 2), lat=48.8, description="x"))
    assert event.pending_events[0].type is DomainEventType.UPDATED
    assert event.pending_events[0].changed_fields == ("startDate", "lat", "description")


def test_editing_without_changes_records_nothing() -> None:
    event = _event(EventStatus.PUBLISHED)
    event.edit(event.content)
    assert event.pending_events == []


def test_cancelled_events_accept_text_changes_only() -> None:
    event = _event(EventStatus.CANCELLED)
    event.edit(replace(event.content, description="Fällt aus wegen Sturm"))
    assert _types(event) == [DomainEventType.UPDATED]

    with pytest.raises(InvalidTransitionError):
        event.edit(replace(event.content, start_date=date(2026, 11, 1)))


def test_changed_fields_compares_every_field() -> None:
    after = replace(COMPLETE, program=(), city="Aalen", opening_hours=("Sa 10-20 Uhr",))
    assert changed_fields(COMPLETE, after) == ("openingHours", "city")
