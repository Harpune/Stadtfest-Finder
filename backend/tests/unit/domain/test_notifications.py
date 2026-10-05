"""Notification rules: settings, triggers, idempotency, texts (R11)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.notifications.notification import (
    PUSH_TEXTS,
    EventFacts,
    NotificationType,
    dedupe_key,
    format_period,
    is_relevant_change,
    render_text,
)
from stadtfest.domain.notifications.settings import (
    Home,
    InvalidSettingsError,
    NotificationSettings,
)

EVENT = UUID("00000000-0000-0000-0000-0000000000e1")
AALEN = Home("73430", "Aalen", GeoPoint(48.8378, 10.0933))
DASH = chr(0x2013)  # en dash
FACTS = EventFacts("Reichsstädter Tage", "Aalen", date(2026, 10, 2), date(2026, 10, 13))


def test_defaults_match_the_design() -> None:
    settings = NotificationSettings()
    assert (settings.remind, settings.remind_days_before, settings.near_radius_km) == (
        True,
        1,
        25,
    )
    assert settings.home is None
    assert settings.change
    assert settings.invite
    assert settings.rsvp


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"remind_days_before": 2}, {"remindDaysBefore"}),
        ({"near_radius_km": 0}, {"nearRadiusKm"}),
        ({"near_radius_km": 155}, {"nearRadiusKm"}),
        ({"near_radius_km": 27}, {"nearRadiusKm"}),
        ({"home": Home("73430", "", AALEN.location)}, {"home.placeName"}),
    ],
)
def test_invalid_settings_name_the_fields(changes: dict[str, object], fields: set[str]) -> None:
    with pytest.raises(InvalidSettingsError) as raised:
        NotificationSettings(**changes)  # type: ignore[arg-type]
    assert set(raised.value.fields) == fields


def test_settings_decide_about_the_push_only() -> None:
    muted = NotificationSettings(remind=False, change=False)
    assert not muted.pushes(NotificationType.REMIND)
    assert not muted.pushes(NotificationType.CHANGE)
    assert not muted.pushes(NotificationType.CANCEL)  # cancellations follow `change`
    assert not NotificationSettings().pushes(NotificationType.NEAR)  # no home yet
    assert NotificationSettings(home=AALEN).pushes(NotificationType.NEAR)


def test_only_date_time_and_place_changes_notify() -> None:
    assert is_relevant_change(["startDate"])
    assert is_relevant_change(["description", "lat", "lon"])
    assert is_relevant_change(["openingHours"])
    assert not is_relevant_change(["description", "price", "name"])
    assert not is_relevant_change([])


def test_dedupe_keys_combine_by_day_hour_or_event() -> None:
    morning = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)  # 09:00 in Berlin
    evening = datetime(2026, 10, 1, 21, 30, tzinfo=UTC)  # 23:30 in Berlin
    remind = NotificationType.REMIND
    assert dedupe_key(remind, EVENT, morning) == dedupe_key(remind, EVENT, evening)
    change = NotificationType.CHANGE
    assert dedupe_key(change, EVENT, morning) == dedupe_key(
        change, EVENT, morning.replace(minute=59)
    )
    assert dedupe_key(change, EVENT, morning) != dedupe_key(change, EVENT, evening)
    near = NotificationType.NEAR
    assert dedupe_key(near, EVENT, morning) == dedupe_key(near, EVENT, evening)


def test_periods_like_in_the_app() -> None:
    assert format_period(date(2026, 12, 12), date(2026, 12, 13)) == f"12.{DASH}13. Dez 2026"
    assert format_period(date(2026, 9, 29), date(2026, 10, 15)) == f"29. Sep {DASH} 15. Okt 2026"
    assert format_period(date(2026, 12, 28), date(2027, 1, 6)) == f"28. Dez 2026 {DASH} 6. Jan 2027"
    assert format_period(date(2026, 5, 1), None) == "1. Mai 2026"
    assert format_period(None, None) == "Termin offen"


def test_list_texts() -> None:
    created = datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
    period = f"2.{DASH}13. Okt 2026"
    assert render_text(NotificationType.REMIND, FACTS, created) == (
        f"Reichsstädter Tage beginnt morgen: {period} in Aalen."
    )
    week_before = datetime(2026, 9, 25, 7, 0, tzinfo=UTC)
    assert "beginnt in einer Woche" in render_text(NotificationType.REMIND, FACTS, week_before)
    assert render_text(NotificationType.NEAR, FACTS, created) == (
        f"Neu in Aalen: Reichsstädter Tage ({period})."
    )
    assert render_text(NotificationType.CHANGE, FACTS, created).startswith(
        "Bei Reichsstädter Tage haben sich Termin, Zeiten oder Ort geändert."
    )
    cancelled = EventFacts("Herbstmarkt", "Oberkochen", date(2026, 9, 27), None, "Bauarbeiten")
    assert render_text(NotificationType.CANCEL, cancelled, created) == (
        "Herbstmarkt (27. Sep 2026) fällt aus. Grund: Bauarbeiten"
    )


def test_push_texts_are_generic() -> None:
    """Push texts must not contain names, event names or places (E-04)."""
    assert set(NotificationType) <= set(PUSH_TEXTS)
    for text in PUSH_TEXTS.values():
        for part in (text.title, text.body):
            assert "{" not in part
            assert not re.search(r"\d", part)
