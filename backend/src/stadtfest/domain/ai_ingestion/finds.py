"""Finds of the AI search (schema `EventDraftV2`) and their checks (R10-US3, R10c)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Version of the fixed output schema; stored in the job log.
DRAFT_SCHEMA_VERSION = "EventDraftV2"

# Germany's bounding box: coordinates outside are implausible and get geocoded again.
_LAT = (47.2, 55.1)
_LON = (5.8, 15.1)

_POSTAL_CITY = re.compile(r"\b(\d{5})\s+([^,\n]+)")
_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|ref|ref_src)$", re.IGNORECASE)
_CLOCK = re.compile(r"^([01]?\d|2[0-4]):([0-5]\d)$")
_WEEKDAYS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
# Limits of `openingHours` in the moderation form (`ModEventFields`).
MAX_OPENING_HOURS = 10


def parse_clock(text: str | None) -> str | None:
    """`18:00`, `9:30` or `24:00` as `HH:MM` (local time Berlin); None if not a clock time."""
    match = _CLOCK.match((text or "").strip())
    if match is None:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours == 24 and minutes:
        return None
    return f"{hours:02d}:{minutes:02d}"


def _short_clock(clock: str) -> str:
    """`18:00` → `18`, `18:30` → `18:30` (style of the opening hours in the catalog)."""
    hours, minutes = clock.split(":")
    return str(int(hours)) if minutes == "00" else f"{int(hours)}:{minutes}"


@dataclass(frozen=True, slots=True)
class DayHours:
    """Opening time of one day of an event, local time Berlin (R10c).

    Times are `HH:MM`; `closes` may be `24:00` or earlier than `opens` (after midnight).
    """

    day: date
    opens: str
    closes: str | None = None

    def line(self) -> str:
        """One line of `openingHours`, e.g. `Fr 12.06. 18-24 Uhr` or `Sa 13.06. ab 11 Uhr`."""
        prefix = f"{_WEEKDAYS[self.day.weekday()]} {self.day:%d.%m.}"
        if self.closes is None:
            return f"{prefix} ab {_short_clock(self.opens)} Uhr"
        return f"{prefix} {_short_clock(self.opens)}-{_short_clock(self.closes)} Uhr"


@dataclass(frozen=True, slots=True)
class FoundEvent:
    """One find in the fixed schema; already structurally valid (types, required fields)."""

    name: str
    date_from: date
    date_to: date
    place: str
    address: str
    source_url: str
    lat: float | None = None
    lon: float | None = None
    category: str | None = None
    description: str | None = None
    # R10c: own website of the event (checked like the source), opening times, price.
    website_url: str | None = None
    opening_hours: tuple[DayHours, ...] = ()
    price: str | None = None

    def opening_hours_lines(self) -> tuple[str, ...]:
        """Opening times within the event's dates as `openingHours` lines, by day."""
        days = sorted(
            {
                h.day: h for h in self.opening_hours if self.date_from <= h.day <= self.date_to
            }.values(),
            key=lambda h: h.day,
        )
        return tuple(h.line() for h in days[:MAX_OPENING_HOURS])

    def overlaps(self, start: date, end: date) -> bool:
        """Whether the event takes place on at least one day of `start`-`end`."""
        return self.date_from <= end and self.date_to >= start

    def problems(self, today: date) -> list[str]:
        """Content problems that make the find invalid (counted, never logged)."""
        found: list[str] = []
        if not self.name.strip():
            found.append("name")
        if self.date_to < self.date_from:
            found.append("dates_reversed")
        if self.date_to < today:
            found.append("past")
        if not is_web_url(self.source_url):
            found.append("source_url")
        return found

    @property
    def plausible_location(self) -> bool:
        """Coordinates given and inside Germany."""
        return (
            self.lat is not None
            and self.lon is not None
            and _LAT[0] <= self.lat <= _LAT[1]
            and _LON[0] <= self.lon <= _LON[1]
        )


def is_web_url(url: str) -> bool:
    """`http(s)://host/...`."""
    parts = urlsplit(url.strip())
    return parts.scheme in {"http", "https"} and bool(parts.netloc)


def normalize_url(url: str) -> str:
    """Comparable form of a source URL.

    https, lower-case host without `www.`, no fragment, no tracking parameters and no
    trailing slash.
    """
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k)))
    path = parts.path.rstrip("/")
    return urlunsplit(("https", host, path, query, ""))


def domain_of(url: str) -> str:
    """Host without `www.` (shown as "Gefunden auf …")."""
    return urlsplit(url.strip()).netloc.lower().removeprefix("www.")


def geocoding_queries(find: FoundEvent) -> list[str]:
    """Queries to locate a find, from exact to coarse.

    Addresses from event pages are often vague ("Innenstadt, 73441 Bopfingen"), which the
    geocoder cannot resolve; then the place within the town, the town and finally the postal
    code are tried. Coarse results only place the pin roughly; moderators check it.
    """
    match = _POSTAL_CITY.search(find.address)
    postal_city = f"{match.group(1)} {match.group(2).strip()}" if match else ""
    candidates = [
        find.address,
        f"{find.place}, {postal_city}" if find.place and postal_city else "",
        postal_city,
        match.group(1) if match else "",
        "" if find.address else find.place,
    ]
    queries: list[str] = []
    for query in (c.strip() for c in candidates):
        if query and query not in queries:
            queries.append(query)
    return queries


def normalize_name(name: str) -> str:
    """Event name for comparisons: case-folded, punctuation and extra spaces removed."""
    return " ".join(re.sub(r"[^\w\s]", " ", name.casefold()).split())
