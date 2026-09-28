"""System clock in Europe/Berlin ("today" for all date rules)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


class BerlinClock:
    """Implements the `Clock` port with the system time."""

    def today(self) -> date:
        """Return the current day in Europe/Berlin."""
        return datetime.now(BERLIN).date()
