from datetime import date

import pytest

from stadtfest.domain.events.event import (
    EventStatus,
    is_listed,
    is_past,
    is_publicly_accessible,
    is_running,
)
from stadtfest.domain.events.geo import BoundingBox, GeoPoint, PostalCode
from stadtfest.domain.events.time_filter import DateRange

TODAY = date(2026, 9, 25)
RUNNING = DateRange(date(2026, 9, 18), date(2026, 9, 27))
ENDED_YESTERDAY = DateRange(date(2026, 9, 20), date(2026, 9, 24))
ENDS_TODAY = DateRange(date(2026, 9, 20), TODAY)


@pytest.mark.parametrize(
    ("status", "deleted", "expected"),
    [
        (EventStatus.PUBLISHED, False, True),
        (EventStatus.CANCELLED, False, True),
        (EventStatus.DRAFT, False, False),
        (EventStatus.PUBLISHED, True, False),
    ],
)
def test_publicly_accessible(status: EventStatus, deleted: bool, expected: bool) -> None:
    assert is_publicly_accessible(status, deleted=deleted) is expected


def test_listed_until_end_day_inclusive() -> None:
    assert is_listed(EventStatus.PUBLISHED, ENDS_TODAY, TODAY, deleted=False)
    assert not is_listed(EventStatus.PUBLISHED, ENDED_YESTERDAY, TODAY, deleted=False)


def test_running_and_past() -> None:
    assert is_running(RUNNING, TODAY)
    assert not is_past(RUNNING, TODAY)
    assert is_past(ENDED_YESTERDAY, TODAY)


def test_geo_validation() -> None:
    with pytest.raises(ValueError, match="latitude"):
        GeoPoint(91, 10)
    with pytest.raises(ValueError, match="wrong order"):
        BoundingBox(11, 48, 10, 49)
    assert BoundingBox(10, 48, 12, 50).center == GeoPoint(49, 11)


def test_postal_code_and_distance() -> None:
    assert str(PostalCode("73430")) == "73430"
    aalen, ulm = GeoPoint(48.8378, 10.0933), GeoPoint(48.3984, 9.9916)
    assert aalen.distance_km(ulm) == pytest.approx(49.5, abs=0.5)
    assert aalen.distance_km(aalen) == 0
    with pytest.raises(ValueError, match="5 digits"):
        PostalCode("7343")
