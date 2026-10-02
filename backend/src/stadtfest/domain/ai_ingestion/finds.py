"""Finds of the AI search (schema `EventDraftV1`) and their checks (R10-US3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Version of the fixed output schema; stored in the job log.
DRAFT_SCHEMA_VERSION = "EventDraftV1"

# Germany's bounding box: coordinates outside are implausible and get geocoded again.
_LAT = (47.2, 55.1)
_LON = (5.8, 15.1)

_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|ref|ref_src)$", re.IGNORECASE)


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
