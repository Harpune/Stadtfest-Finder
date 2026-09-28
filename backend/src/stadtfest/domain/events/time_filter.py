"""Date ranges and the public time filter (Alle Termine, Heute, Wochenende, Monate)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

SATURDAY = 5
MAX_MONTHS = 12


@dataclass(frozen=True, slots=True)
class DateRange:
    """An inclusive range of calendar days."""

    start: date
    end: date

    def __post_init__(self) -> None:
        """Validate that the range is not inverted."""
        if self.end < self.start:
            raise ValueError("end date is before start date")

    def overlaps(self, other: DateRange) -> bool:
        """Return True if both ranges share at least one day."""
        return self.start <= other.end and other.start <= self.end

    def contains(self, day: date) -> bool:
        """Return True if `day` lies within the range."""
        return self.start <= day <= self.end


@dataclass(frozen=True, order=True, slots=True)
class YearMonth:
    """A calendar month, e.g. 2026-10."""

    year: int
    month: int

    def __post_init__(self) -> None:
        """Validate the month number."""
        if not 1 <= self.month <= 12:
            raise ValueError("month must be between 1 and 12")

    @classmethod
    def parse(cls, value: str) -> YearMonth:
        """Parse `YYYY-MM`.

        Args:
            value: Month in ISO format.

        Returns:
            The parsed month.

        Raises:
            ValueError: If the format is invalid.
        """
        year, sep, month = value.partition("-")
        if not sep or len(year) != 4 or len(month) != 2 or not (year + month).isdigit():
            raise ValueError("month must have the format YYYY-MM")
        return cls(int(year), int(month))

    def as_range(self) -> DateRange:
        """Return the month as a date range."""
        last_day = calendar.monthrange(self.year, self.month)[1]
        return DateRange(date(self.year, self.month, 1), date(self.year, self.month, last_day))

    def __str__(self) -> str:
        """Return `YYYY-MM`."""
        return f"{self.year:04d}-{self.month:02d}"


class TimeFilterKind(StrEnum):
    """Time filter options of the filter sheet (E-03: month grid, no free calendar)."""

    ALL = "all"
    TODAY = "today"
    WEEKEND = "weekend"
    MONTHS = "months"


@dataclass(frozen=True, slots=True)
class TimeFilter:
    """The selected time filter."""

    kind: TimeFilterKind = TimeFilterKind.ALL
    months: tuple[YearMonth, ...] = ()

    def __post_init__(self) -> None:
        """Validate that months are given exactly when required."""
        if self.kind is TimeFilterKind.MONTHS and not self.months:
            raise ValueError("when=months requires at least one month")
        if len(self.months) > MAX_MONTHS:
            raise ValueError(f"at most {MAX_MONTHS} months")

    def windows(self, today: date) -> tuple[DateRange, ...] | None:
        """Return the date ranges an event must overlap, or None for "all dates".

        Args:
            today: The current day in Europe/Berlin.

        Returns:
            - `today`: the current day.
            - `weekend`: Saturday and Sunday of the current week; on Sunday only Sunday.
            - `months`: one range per selected month.
            - `all`: None (no restriction).
        """
        match self.kind:
            case TimeFilterKind.ALL:
                return None
            case TimeFilterKind.TODAY:
                return (DateRange(today, today),)
            case TimeFilterKind.WEEKEND:
                saturday = today + timedelta(days=SATURDAY - today.weekday())
                sunday = saturday + timedelta(days=1)
                return (DateRange(max(today, saturday), sunday),)
            case TimeFilterKind.MONTHS:
                return tuple(month.as_range() for month in sorted(set(self.months)))
