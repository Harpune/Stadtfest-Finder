from datetime import date

import pytest

from stadtfest.domain.events.time_filter import (
    DateRange,
    TimeFilter,
    TimeFilterKind,
    YearMonth,
)

FRIDAY = date(2026, 9, 25)  # reference date of the design prototype
SATURDAY = date(2026, 9, 26)
SUNDAY = date(2026, 9, 27)


def test_all_has_no_window() -> None:
    assert TimeFilter().windows(FRIDAY) is None


def test_today_is_the_current_day() -> None:
    assert TimeFilter(TimeFilterKind.TODAY).windows(FRIDAY) == (DateRange(FRIDAY, FRIDAY),)


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 9, 21), DateRange(SATURDAY, SUNDAY)),  # Monday
        (FRIDAY, DateRange(SATURDAY, SUNDAY)),
        (SATURDAY, DateRange(SATURDAY, SUNDAY)),
        (SUNDAY, DateRange(SUNDAY, SUNDAY)),  # only Sunday is left
    ],
)
def test_weekend_is_saturday_and_sunday_of_current_week(today: date, expected: DateRange) -> None:
    assert TimeFilter(TimeFilterKind.WEEKEND).windows(today) == (expected,)


def test_months_cover_whole_months_across_year_end() -> None:
    months = (YearMonth.parse("2027-01"), YearMonth.parse("2026-12"), YearMonth.parse("2026-12"))
    windows = TimeFilter(TimeFilterKind.MONTHS, months).windows(FRIDAY)
    assert windows == (
        DateRange(date(2026, 12, 1), date(2026, 12, 31)),
        DateRange(date(2027, 1, 1), date(2027, 1, 31)),
    )


def test_february_leap_year() -> None:
    assert YearMonth(2028, 2).as_range().end == date(2028, 2, 29)


def test_months_filter_requires_months() -> None:
    with pytest.raises(ValueError, match="requires"):
        TimeFilter(TimeFilterKind.MONTHS)


def test_at_most_twelve_months() -> None:
    months = tuple(YearMonth(2026 + (m // 12), m % 12 + 1) for m in range(13))
    with pytest.raises(ValueError, match="at most"):
        TimeFilter(TimeFilterKind.MONTHS, months)


@pytest.mark.parametrize("value", ["2026-13", "2026-1", "26-01", "2026/01", "abcd-ef", ""])
def test_invalid_months_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):  # noqa: PT011  # message differs per case
        YearMonth.parse(value)


def test_overlap_includes_boundaries() -> None:
    event = DateRange(date(2026, 9, 18), date(2026, 9, 27))
    assert event.overlaps(DateRange(SUNDAY, SUNDAY))
    assert not event.overlaps(DateRange(date(2026, 9, 28), date(2026, 9, 30)))


def test_inverted_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="before"):
        DateRange(SUNDAY, FRIDAY)
